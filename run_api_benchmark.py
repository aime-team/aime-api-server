# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from aime_api_client_interface import do_api_request_async
import toml
import asyncio
import argparse
import time
from tqdm import tqdm
from collections import Counter

class BenchmarkApiEndpoint():

    def __init__(self):
        self.args = self.load_flags()
        self.progress_bar_dict = dict()
        self.title_bar = tqdm(total=0, bar_format='{desc}', leave=False)
        self.num_generated_tokens = 480
        self.num_finished_tasks = 0
        self.start_time_after_warmup = time.time() # updated after warmup if self.args.warmup_requests > 0


    def load_flags(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument(
            '-as', '--api_server', type=str, default="http://0.0.0.0:7777", required=False, help='Address of the API server'
        )
        parser.add_argument(
            '-tr', '--total_requests', type=int, default=4, required=False, help='Total number of requests'
        )
        parser.add_argument(
            '-cr', '--concurrent_requests', type=int, default=40, required=False, help='Number of concurrent asynchronous requests limited with asyncio.Semaphore()'
        )
        parser.add_argument(
            '-cf', '--config_file', type=str, required=False, help='To change address of endpoint config file to get the default values of the job parameters. '
        )
        parser.add_argument(
            '-ep', '--endpoint_name', type=str, default='llama2_chat', required=False, help='Name of the endpoint'
        )
        parser.add_argument(
            '-wr', '--warmup_requests', type=int, default=1, required=False, help='Number of warmup requests for calculation of additional mean results'
        )
        args = parser.parse_args()
        if not args.config_file:
            if args.endpoint_name == 'stable_diffusion_xl_txt2img':
                args.config_file = 'endpoints/stable_diffusion_xl/txt2img/aime_api_endpoint.cfg'
            else:
                args.config_file = f'endpoints/{args.endpoint_name}/aime_api_endpoint.cfg'
        return args

    def print_start_message(self, params):
        print(
            f'Starting Benchmark on {self.args.api_server}/{self.args.endpoint_name} with\n'
            f'{self.args.total_requests} total requests\n'
            f'{self.args.concurrent_requests} concurrent requests\n'
            f'{self.args.warmup_requests} warmup requests\n'
            f'Job parameters:'
        )
        for key, value in params.items():
            print(f'{key}: {value}')
        print()


    def get_default_values_from_config(self):
        with open(self.args.config_file, "r") as f:
            config = toml.load(f)
        ep_inputs = config.get('INPUTS', {})
        params = dict()
        for ep_input in ep_inputs:
            params[ep_input] = ep_inputs[ep_input].get('default')
        if params.get('seed'):
            params['seed'] = 1
        if params.get('top_k'):
            params['top_k'] = 1
            params['top_p'] = 1
            params['text'] = 'Once upon a time'
        return params

    async def do_request(self, params, semaphore):
        async with semaphore:
            await do_api_request_async(self.args.api_server, self.args.endpoint_name, params, 'aime', '6a17e2a5b70603cb1a3294b4a1df67da', self.result_callback, self.progress_callback)

    def run(self):
        params = self.get_default_values_from_config()
        self.print_start_message(params)
        loop = self.get_loop()
        start = time.time()
        semaphore = asyncio.Semaphore(self.args.concurrent_requests)
        tasks = [asyncio.ensure_future(self.do_request(params, semaphore)) for _ in range(self.args.total_requests)]
        loop.run_until_complete(asyncio.gather(*tasks))
        stop = time.time()
        duration = round(stop - start)
        duration_without_warmup = round(stop - self.start_time_after_warmup)
        self.title_bar.close()
        if self.args.endpoint_name == 'llama2_chat':
            mean_result_string = f'; {round((self.args.total_requests*self.num_generated_tokens)/duration, 1)} tokens/s'
            mean_result_string_warmup = f'; {round(((self.args.total_requests - self.args.warmup_requests)*self.num_generated_tokens)/duration_without_warmup, 1)} tokens/s'
        else:
            mean_result_string = f'; {round(self.args.total_requests/duration, 1)} images/s'
            mean_result_string_warmup = f'; {round((self.args.total_requests - self.args.warmup_requests)/duration_without_warmup, 1)} images/s'

        print(
            '---------------------------------'
            '\nFinished'
            '\n---------------------------------\n'
            '\nResult:'
            f'\n\n{self.args.total_requests} requests with {self.args.concurrent_requests} concurrent requests took {duration} seconds.'
            f'\nMean time per request: {round(duration/self.args.total_requests, 1)}s {mean_result_string}'
        )
        if self.args.warmup_requests:
            print(
            f'\nExcluding the first {self.args.warmup_requests} warmup requests:'
            f'\n{self.args.total_requests - self.args.warmup_requests} requests with {self.args.concurrent_requests} concurrent requests took {duration_without_warmup} seconds.' \
            f'\nMean time per request: {round(duration_without_warmup/(self.args.total_requests - self.args.warmup_requests), 1)}s {mean_result_string_warmup}'
            )
        
    def get_loop(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def progress_callback(self, progress_info, progress_data):
        job_id = progress_info['job_id']
        if not self.progress_bar_dict.get(job_id):
            if progress_info['queue_position'] == 0:
                self.progress_bar_dict[job_id] = tqdm(range(0, 100), desc=f'Current job: {job_id}', leave=False)
            else:
                self.progress_bar_dict[job_id] = None

        self.title_bar.set_description_str(f'Remaining jobs: {self.args.total_requests - self.num_finished_tasks} / {self.args.total_requests}')
        current_progress_bar = self.progress_bar_dict[job_id]
        if current_progress_bar:
            if self.args.endpoint_name == 'llama2_chat':
                current_progress_bar.n = round(100*progress_info['progress']/self.num_generated_tokens)
            else:
                current_progress_bar.n = progress_info['progress']
            current_progress_bar.refresh()
            current_progress_bar.set_description(f'Current job: {job_id}')
            #self.remove_progress_bar_when_finished(job_id)
        

    def result_callback(self, result):
        self.num_finished_tasks += 1
        if self.num_finished_tasks == self.args.warmup_requests:
            self.start_time_after_warmup = time.time()
        self.num_generated_tokens = result.get('num_generated_tokens')
        self.remove_progress_bar_when_finished(result['job_id'])
        
        #result.pop('images')
        #print('result ', result)
        
    def remove_progress_bar_when_finished(self, job_id):
        current_progress_bar = self.progress_bar_dict.get(job_id)
        if current_progress_bar:# or progress_info['progress'] == 100:
            current_progress_bar.close()
            del self.progress_bar_dict[job_id]



def main():
    benchmark_api = BenchmarkApiEndpoint()
    benchmark_api.run()


if __name__ == "__main__":
	main()

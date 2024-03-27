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
        self.params = self.get_default_values_from_config()
        self.semaphore = asyncio.Semaphore(self.args.concurrent_requests)
        self.progress_bar_dict = dict()
        self.title_bar_1 = tqdm(total=0, bar_format='{desc}', leave=False, position=0)
        self.title_bar_2 = tqdm(total=0, bar_format='{desc}', leave=False, position=1)
        self.num_generated_tokens = 480
        self.num_finished_tasks = 0
        self.start_time = time.time()
        self.start_time_second_batch = time.time() # updated after warmup if self.args.warmup_requests > 0
        self.first_batch = True
        self.jobs_first_batch = dict()
        self.num_jobs_first_batch = 0


    def load_flags(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument(
            '-as', '--api_server', type=str, default="http://0.0.0.0:7777", required=False, help='Address of the API server'
        )
        parser.add_argument(
            '-tr', '--total_requests', type=int, default=4, required=False, help="Total number of requests. Choose a multiple of the worker's batchsize to have a full last batch"
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
            '-tfb', '--time_to_get_first_batch_jobs', type=int, default=1, required=False, help='Time in seconds after start to get the number of jobs in the first batch'
        )
        args = parser.parse_args()
        if not args.config_file:
            if args.endpoint_name == 'stable_diffusion_xl_txt2img':
                args.config_file = 'endpoints/stable_diffusion_xl/txt2img/aime_api_endpoint.cfg'
            else:
                args.config_file = f'endpoints/{args.endpoint_name}/aime_api_endpoint.cfg'
        return args

    def print_start_message(self):
        print(
            f'Starting Benchmark on {self.args.api_server}/{self.args.endpoint_name} with\n'
            f'{self.args.total_requests} total requests\n'
            f'{self.args.concurrent_requests} concurrent requests\n'
            f'Time after jobs in first batch got checked: {self.args.time_to_get_first_batch_jobs}s\n'
            f'Job parameters:'
        )
        for key, value in self.params.items():
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

    async def do_request_with_semaphore(self):
        """Limits the concurrent requests
        """
        async with self.semaphore:
            await do_api_request_async(self.args.api_server, self.args.endpoint_name, self.params, 'aime', '6a17e2a5b70603cb1a3294b4a1df67da', self.result_callback, self.progress_callback)

    def run(self):
        self.print_start_message()
        loop = self.get_loop()
        tasks = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=loop) for _ in range(self.args.total_requests)]
        loop.run_forever()
        duration = time.time() - self.start_time_second_batch
        self.title_bar_1.close()
        self.title_bar_2.close()
        if self.args.endpoint_name == 'llama2_chat':
            mean_result_string = f'| {round((self.args.total_requests*self.num_generated_tokens)/duration, 1)} tokens/s'
        else:
            mean_result_string = f'| {round(self.args.total_requests/duration, 1)} images/s'

        print(
            '\n---------------------------------\n'
            'Finished'
            '\n---------------------------------\n\n'
            'Result:\n'
            f'First batch containing {self.num_jobs_first_batch} jobs being skipped.\n'
            f'{self.args.total_requests} requests with {self.args.concurrent_requests} concurrent requests took {round(duration)} seconds.\n'
            f'Mean time per request: {round(duration/self.args.total_requests, 1)}s {mean_result_string}'
        )


    def get_loop(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop


    async def progress_callback(self, progress_info, progress_data):
        job_id = progress_info['job_id']

        if not self.progress_bar_dict.get(job_id):
            if progress_info['queue_position'] == 0:
                self.progress_bar_dict[job_id] = tqdm(range(0, 100), desc=f'Job ID: {job_id}', leave=False)
        self.num_current_running_jobs = sum([1 for progress_bar in self.progress_bar_dict.values() if progress_bar.n])
        if not self.num_jobs_first_batch:
            if (time.time() - self.start_time) >= self.args.time_to_get_first_batch_jobs:
                self.jobs_first_batch = {job_id: progress_bar for job_id, progress_bar in self.progress_bar_dict.items() if progress_bar.n}
                self.num_jobs_first_batch = self.num_current_running_jobs
                loop = self.get_loop()
                _ = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=loop) for _ in range(self.num_jobs_first_batch)]
        else:
            if self.first_batch and progress_info.get('progress') and progress_info.get('job_id') not in self.jobs_first_batch.keys():
                self.first_batch = False
                self.start_time_second_batch = time.time()
        self.update_title()
        current_progress_bar = self.progress_bar_dict.get(job_id)
        if current_progress_bar:
            if self.args.endpoint_name == 'llama2_chat':
                current_progress_bar.n = round(100*progress_info['progress']/self.num_generated_tokens)
            else:
                current_progress_bar.n = progress_info['progress']
            current_progress_bar.refresh()
            current_progress_bar.set_description(f'Job ID: {job_id}')


    def update_title(self):
        if self.first_batch:
            title_str_1 = f'Processing first batch! Not taken into account for benchmark results!'
            if self.num_jobs_first_batch:
                title_str_1 += f' Remaining jobs in first batch: {self.num_jobs_first_batch - self.num_finished_tasks} / {self.num_jobs_first_batch}'
        else:
            title_str_1 = f'Warmup stage with first batch containing {self.num_jobs_first_batch} jobs finished. Benchmark running.'
            title_str_2 = f'Remaining jobs: {self.args.total_requests + self.num_jobs_first_batch - self.num_finished_tasks} / {self.args.total_requests} | Current running jobs: {self.num_current_running_jobs}'
            self.title_bar_2.set_description_str(title_str_2)
        self.title_bar_1.set_description_str(title_str_1)


    async def result_callback(self, result):
        self.num_finished_tasks += 1
        if self.first_batch:
            self.first_batch = False
            self.start_time_second_batch = time.time()
        if self.num_finished_tasks == self.args.total_requests + self.num_jobs_first_batch:
            self.get_loop().stop()
        self.num_generated_tokens = result.get('num_generated_tokens')
        self.remove_progress_bar(result['job_id'])
        
        

    def remove_progress_bar(self, job_id):
        current_progress_bar = self.progress_bar_dict.get(job_id)       
        
        if current_progress_bar:
            current_position = current_progress_bar.pos
            current_progress_bar.close()
            del self.progress_bar_dict[job_id]
            

def main():
    benchmark_api = BenchmarkApiEndpoint()
    benchmark_api.run()


if __name__ == "__main__":
	main()

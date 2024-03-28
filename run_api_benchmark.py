# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from aime_api_client_interface import do_api_request_async
import toml
import asyncio
import argparse
import time
from tqdm.asyncio import tqdm
from collections import Counter

class BenchmarkApiEndpoint():

    def __init__(self):
        self.args = self.load_flags()
        self.params = self.get_default_values_from_config()
        self.semaphore = asyncio.Semaphore(self.args.concurrent_requests)
        self.progress_bar_dict = dict()
        self.title_bar_list = [tqdm(total=0, bar_format='{desc}', leave=False, position=i) for i in range(10)]
        self.num_generated_tokens = 480
        self.num_finished_jobs = 0
        self.start_time = time.time()
        self.start_time_second_batch = None
        self.first_batch = True
        self.jobs_first_batch = dict()
        self.num_jobs_first_batch = 0
        self.endpoint_version = None
        self.model_name = None
        self.worker_names = set()
        self.worker_interface_version = None


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

    
    def run(self):
        self.print_start_message()
        self.update_meta_data_in_title()
        self.make_table_title()
        loop = self.get_loop()
        tasks = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=loop) for _ in range(self.args.total_requests)]
        loop.run_forever()
        duration = time.time() - self.start_time_second_batch
        for title_bar in self.title_bar_list:
            title_bar.close()
        benchmark_result_string = self.make_benchmark_result_string()
        print(
            '\n---------------------------------\n'
            'Finished'
            '\n---------------------------------\n\n'
            'Result:\n'
            f'First batch containing {self.num_jobs_first_batch} jobs being skipped.\n'
            f'Number of detected workers: {len(self.worker_names)}\n'
            f'Worker names: {", ".join(worker_name for worker_name in self.worker_names)}\n'
            f'Worker Interface version: {self.worker_interface_version}\n'
            f'Endpoint version: {self.endpoint_version}\n'
            f'Model name: {self.model_name}\n'
            f'{self.args.total_requests} requests with {self.args.concurrent_requests} concurrent requests took {round(duration)} seconds.\n'
            f'{benchmark_result_string}'
        )


    async def progress_callback(self, progress_info, progress_data):
        job_id = progress_info.get('job_id')
        if not self.progress_bar_dict.get(job_id) and progress_info.get('queue_position') == 0:
            self.init_progress_bar(job_id)
        self.update_progress_bar(progress_info)
        self.num_current_running_jobs = sum([1 for progress_bar in self.progress_bar_dict.values() if progress_bar.n])
        if self.first_batch:
            self.handle_first_batch(progress_info)
        self.update_title()
        


    async def result_callback(self, result):
        self.num_generated_tokens = result.get('num_generated_tokens')
        self.num_finished_jobs += 1
        if self.first_batch: # If result_callback of first batch is called before progress_callback of second batch
            self.first_batch = False
            self.start_time_second_batch = time.time()
        self.process_meta_data(result)
        self.update_title(True)
        if self.num_finished_jobs == self.args.total_requests + self.num_jobs_first_batch:
            self.get_loop().stop()
        self.remove_progress_bar(result.get('job_id'))

    def make_table_title(self):
        self.title_bar_list[8].set_description_str('JOB ID      Progress ')


    def init_progress_bar(self, job_id):
        if self.args.endpoint_name == 'llama2_chat':
            total = self.num_generated_tokens
            unit = ' tokens'
        else:
            total = 1
            unit = ' images'
        self.progress_bar_dict[job_id] = tqdm(
            total=total,
            unit=unit,
            desc=f'{job_id:>10}',
            leave=False,
            bar_format='{desc} {percentage:3.0f}% {bar}| {n_fmt}/{total_fmt} {elapsed} < {remaining} , ' '{rate_fmt} {postfix}'
            )


    def handle_first_batch(self, progress_info):
        job_id = progress_info.get('job_id')
        if not self.num_jobs_first_batch:
            if (time.time() - self.start_time) >= self.args.time_to_get_first_batch_jobs:
                self.jobs_first_batch = {job_id: progress_bar for job_id, progress_bar in self.progress_bar_dict.items() if progress_bar.n}
                self.num_jobs_first_batch = self.num_current_running_jobs
                loop = self.get_loop()
                _ = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=loop) for _ in range(self.num_jobs_first_batch)]
        else:
            if progress_info.get('progress') and job_id not in self.jobs_first_batch.keys(): # If progress_callback of second batch is called before result_callback of first batch
                self.first_batch = False
                self.start_time_second_batch = time.time()


    def update_title(self, job_finished=False):
        if self.first_batch:
            first_batch_title_line = f'Processing first batch for warmup! Results not taken into account for benchmark!'
            if self.num_jobs_first_batch:
                first_batch_title_line += f' Jobs in first batch: {self.num_jobs_first_batch}'
            self.title_bar_list[0].set_description_str(first_batch_title_line)
        else:
            self.title_bar_list[0].set_description_str(
                f'Warmup stage with first batch containing {self.num_jobs_first_batch} jobs finished. ' \
                    f'Benchmark running for {round(time.time() - self.start_time_second_batch)}s'
            )
            self.title_bar_list[6].set_description_str(
                f'Remaining jobs: {self.args.total_requests + self.num_jobs_first_batch - self.num_finished_jobs} / {self.args.total_requests}' \
                f' | Current running jobs: {self.num_current_running_jobs}')
            if job_finished:
                self.update_meta_data_in_title()
                self.title_bar_list[7].set_description_str(self.make_benchmark_result_string())



    def update_meta_data_in_title(self):
        descriptions = [
            f'Number of detected workers: {len(self.worker_names) if self.worker_names else "Available after first batch..."}',
            f'Worker names: {", ".join(self.worker_names) if self.worker_names else "Available after first batch..."}',
            f'Worker Interface version: {self.worker_interface_version if self.worker_interface_version else "Available after first batch..."}',
            f'Endpoint version: {self.endpoint_version if self.endpoint_version else "Available after first batch..."}',
            f'Model name: {self.model_name if self.model_name else "Available after first batch..."}'
        ]

        for line, description in enumerate(descriptions, start=1):
            self.title_bar_list[line].set_description_str(description)
    

    def update_progress_bar(self, progress_info):
        job_id = progress_info.get('job_id')
        current_progress_bar = self.progress_bar_dict.get(job_id)
        if current_progress_bar:
            current_progress = progress_info.get('progress')
            if self.args.endpoint_name == 'llama2_chat':
                if self.num_generated_tokens < current_progress:
                    current_progress_bar.total = current_progress
                else:
                    current_progress_bar.total = self.num_generated_tokens
                current_progress_bar.n = current_progress
            else:
                current_progress_bar.n = current_progress / 100
            current_progress_bar.refresh()
            current_progress_bar.set_description_str(f'{job_id:<10}')


    def make_benchmark_result_string(self):
        if self.num_finished_jobs > self.num_jobs_first_batch:
            duration = time.time() - self.start_time_second_batch
            if self.args.endpoint_name == 'llama2_chat':
                mean_result_string = f'{round((self.num_finished_jobs - self.num_jobs_first_batch) * self.num_generated_tokens / duration, 1)} tokens/s'
            else:
                mean_result_string = f'{round((self.num_finished_jobs - self.num_jobs_first_batch) / duration, 1)} images/s'

            return f'Mean time per request: {round(duration/self.num_finished_jobs, 1)}s | {mean_result_string}'


    def remove_progress_bar(self, job_id):
        current_progress_bar = self.progress_bar_dict.get(job_id)     
        if current_progress_bar:
            current_position = current_progress_bar.pos
            current_progress_bar.close()
            del self.progress_bar_dict[job_id]
            self.remove_empty_line(current_position)


    def remove_empty_line(self, position):
        for progress_bar in self.progress_bar_dict.values():
            if progress_bar.pos > position:
                current_position = progress_bar.pos
                progress_bar.clear(nolock=False)
                progress_bar.pos = current_position -1


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


    def get_loop(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def process_meta_data(self, result):
        self.endpoint_version = result.get('ep_version')
        self.model_name = result.get('model_name')
        self.worker_names.add(result.get('auth'))
        self.worker_interface_version = result.get('worker_interface_version')


def main():
    benchmark_api = BenchmarkApiEndpoint()
    benchmark_api.run()


if __name__ == "__main__":
	main()

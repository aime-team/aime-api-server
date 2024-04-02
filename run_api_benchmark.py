# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from aime_api_client_interface import ModelAPI
import toml
import asyncio
import argparse
import time
from tqdm.asyncio import tqdm
from collections import Counter
import json

class BenchmarkApiEndpoint():
    """Benchmark tool to measure and monitor the performance of GPUs with multiple asynchronous requests on llama2_chat and stable_diffusion_xl_txt2img endpoints.
    """    

    def __init__(self):
        
        self.args = self.load_flags()
        self.model_api = ModelAPI(
            self.args.api_server,
            self.args.endpoint_name,
            self.args.user_name,
            self.args.login_key
        )
        self.model_api.do_api_login()
        self.params = self.get_default_values_from_config()
        self.semaphore = asyncio.Semaphore(self.args.concurrent_requests)
        self.progress_bar_dict = dict()
        self.title_bar_list = [tqdm(total=0, bar_format='{desc}', leave=False, position=i, dynamic_ncols=True) for i in range(10)]
        self.num_generated_units = self.args.num_units
        self.num_current_running_jobs = 0
        self.unit = self.get_unit()
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
        self.first_batch_jobs_added = False


    def load_flags(self):
        """Parsing the command line arguments.

        Returns:
            argparse.Namespace: The argparse object containing the command line arguments
        """        
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument(
            '-as', '--api_server', type=str, default="http://0.0.0.0:7777", required=False, help='Address of the AIME API Server'
        )
        parser.add_argument(
            '-tr', '--total_requests', type=int, default=4, required=False, help="Total number of requests. Choose a multiple of the worker's batchsize to have a full last batch"
        )
        parser.add_argument(
            '-cr', '--concurrent_requests', type=int, default=40, required=False, help='Number of concurrent asynchronous requests limited with asyncio.Semaphore()'
        )
        parser.add_argument(
            '-cf', '--config_file', type=str, required=False, help='To change address of endpoint config file to get the default values of the job parameters'
        )
        parser.add_argument(
            '-ep', '--endpoint_name', type=str, default='llama2_chat', required=False, help='Name of the endpoint'
        )
        parser.add_argument(
            '-ut', '--unit', type=str, required=False, help='Unit of the generated objects. Default: "tokens" if endpoint_name is "llama2_chat" else  "images"'
        )
        parser.add_argument(
            '-t', '--time_to_get_first_batch_jobs', type=int, default=4, required=False, help='Time in seconds after start to get the number of jobs in the first batch'
        )
        parser.add_argument(
            '-u', '--user_name', type=str, default='aime', required=False, help='User name to login on AIME API Server'
        )
        parser.add_argument(
            '-k', '--login_key', type=str, default='6a17e2a5b70603cb1a3294b4a1df67da', required=False, help='Login key related to the user name received from AIME to login on AIME API Server'
        )
        parser.add_argument(
            '-nu', '--num_units', default=1, type=int, required=False, help='Number of units to generate. Images for stable_diffusion_xl_txt2img'
        )
        
        args = parser.parse_args()
        if not args.config_file:
            if args.endpoint_name == 'stable_diffusion_xl_txt2img':
                args.config_file = 'endpoints/stable_diffusion_xl/txt2img/aime_api_endpoint.cfg'
            elif args.endpoint_name == 'llama2_chat':
                args.num_units = 480
                args.config_file = f'endpoints/{args.endpoint_name}/aime_api_endpoint.cfg'
        return args

    
    def run(self):
        """Starting the benchmark.
        """

        self.print_start_message()
        self.update_meta_data_in_title()
        self.make_table_title()
        loop = self.get_loop()
        tasks = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=loop) for _ in range(self.args.total_requests)]
        loop.run_forever()


    async def progress_callback(self, progress_info, progress_data):
        """Called when job progress is received from the API Server. Initializes or updates the job related progress bar, 
        updates the title and measures the number of current running jobs.

        Args:
            progress_info (dict): Job progress information containing the job_id and the progress state like number of generated tokens so far or percentage.
            progress_data (dict): The already generated content like tokens or interim images.
        """        
        job_id = progress_info.get('job_id')
        await self.handle_first_batch(progress_info)
        if not self.progress_bar_dict.get(job_id) and progress_info.get('queue_position') == 0:
            self.init_progress_bar(job_id)
        self.update_progress_bar(progress_info)
        self.num_current_running_jobs = sum([1 for progress_bar in self.progress_bar_dict.values() if progress_bar.n])

        self.update_title()
        

    async def result_callback(self, result):
        """Called when the final job result is received. Removes the job related progress bar, processes information 
        about the server and the worker and updates the title.

        Args:
            result (dict): The final job result like a generated text, audio or images.
        """
        if result.get('success'):
            if result.get('num_generated_tokens'):
                self.num_generated_units = result.get('num_generated_tokens')
            self.num_finished_jobs += 1
            if self.first_batch: # If result_callback of first batch is called before progress_callback of second batch
                self.first_batch = False
                self.start_time_second_batch = time.time()
                
            self.process_meta_data(result)
            self.update_title(True)
            self.remove_progress_bar(result.get('job_id'))
            if self.num_finished_jobs == self.args.total_requests + self.num_jobs_first_batch:
                self.get_loop().stop()
                self.print_benchmark_summary_string()
                await self.model_api.close_session()


    def print_benchmark_summary_string(self):
        """Printing the benchmark summary and the results.
        """
        for title_bar in self.title_bar_list:
            title_bar.close()
        benchmark_result_string = self.make_benchmark_result_string()
        print(
            '\n---------------------------------\n'
            'Finished'
            '\n---------------------------------\n\n'
            'Result:\n'
            f'Number of jobs in first batch: {self.num_jobs_first_batch}\n'
            f'Number of detected workers: {len(self.worker_names)}\n'
            f'Worker names: {", ".join(worker_name for worker_name in self.worker_names)}\n'
            f'Worker Interface version: {self.worker_interface_version}\n'
            f'Endpoint version: {self.endpoint_version}\n'
            f'Model name: {self.model_name}\n'
            f'{self.args.total_requests} requests with {self.args.concurrent_requests} concurrent requests took {round(time.time() - self.start_time_second_batch)} seconds.\n'
            f'{benchmark_result_string}'
        )

    def make_table_title(self):
        """Make Legend title bar for the progress bars.
        """        
        screen_width = self.title_bar_list[8].ncols
        
        column_lengend_left_part = 'JOB ID      Progress in percentage'
        column_lengend_rigth_part = f'| Gen. {self.unit}| Elapsed | Remain | Benchmark'
        dynamic_space = ' ' * (screen_width - len(column_lengend_left_part + column_lengend_rigth_part))
        self.title_bar_list[8].set_description_str(column_lengend_left_part + dynamic_space  + column_lengend_rigth_part)


    def init_progress_bar(self, job_id):
        """Initializing the progress bar of the job with the given job ID.

        Args:
            job_id (str): Job ID of the related job
        """        
        if self.args.endpoint_name == 'llama2_chat':
            total = self.num_generated_units
            unit_scale = False
        else:
            total = 100
            unit_scale = self.num_generated_units  / 100
            precision = 2

        self.progress_bar_dict[job_id] = tqdm(
            total = total,
            unit=' ' + self.unit,
            unit_scale=unit_scale,
            desc=f'{job_id:>10}',
            leave=False,
            bar_format='{desc} {percentage:3.0f}% {bar}| {n:.2f}/{total_fmt} {elapsed} < {remaining} , ' '{rate_noinv_fmt} {postfix}',
            dynamic_ncols=True,
            colour='blue'
            )


    async def handle_first_batch(self, progress_info):
        """Detecting the jobs of the first batch to exclude them from the benchmark results.

        Args:
            progress_info (dict): Job progress information containing the job_id and the progress state like number of generated tokens so far or percentage.
        """        
        job_id = progress_info.get('job_id')
        
        if (time.time() - self.start_time) <= self.args.time_to_get_first_batch_jobs:
            if self.first_batch:
                if self.num_jobs_first_batch < self.num_current_running_jobs:
                    self.jobs_first_batch = {job_id: progress_bar for job_id, progress_bar in self.progress_bar_dict.items() if progress_bar.n}
                    self.num_jobs_first_batch = self.num_current_running_jobs# - self.num_finished_jobs
            else:
                self.get_loop().stop()
                for progress_bar in self.progress_bar_dict.values():
                    progress_bar.close()
                self.title_bar_list[6].close()
                self.title_bar_list[8].close()
                print('\n\n\n\n\n\n\nFirst batch finished before --time_to_get_first_batch_jobs. Choose a shorter time via command line argument!')
                
                #if not self.first_batch_jobs_added:    
                #    loop = self.get_loop()
                #    _ = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=loop) for _ in range(self.num_jobs_first_batch)]
                #    self.first_batch_jobs_added = True
        else:
            if not self.first_batch_jobs_added:
                loop = self.get_loop()
                _ = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=loop) for _ in range(self.num_jobs_first_batch)]
                self.first_batch_jobs_added = True
            if self.first_batch and progress_info.get('progress') and job_id not in self.jobs_first_batch.keys(): # If progress_callback of second batch is called before result_callback of first batch
                self.first_batch = False
                self.start_time_second_batch = time.time()


    def update_title(self, job_finished=False):
        """Updating the title bars for the header containing information about the benchmark.

        Args:
            job_finished (bool, optional): Whether progress or final job result was received. Defaults to False.
        """        
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
        """Updating the title bars with information about the API server and the workers.
        """        
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
        """Updating the related progress bar with the given progress state.

        Args:
            progress_info (dict): Job progress information containing the job_id and the progress state like number of generated tokens so far or percentage.
        """        
        job_id = progress_info.get('job_id')
        current_progress_bar = self.progress_bar_dict.get(job_id)
        if current_progress_bar:
            current_progress = progress_info.get('progress')
            if self.args.endpoint_name == 'llama2_chat':
                if self.num_generated_units < current_progress:
                    current_progress_bar.total = current_progress
                else:
                    current_progress_bar.total = self.num_generated_units
                current_progress_bar.n = current_progress
            else:
                current_progress_bar.n = current_progress
            current_progress_bar.refresh(nolock=False)

            current_progress_bar.set_description_str(f'{job_id:<10}')


    def make_benchmark_result_string(self):
        """Making string containing mean benchmark results.

        Returns:
            str: Result string
        """        

        if self.num_finished_jobs > self.num_jobs_first_batch:
            duration = time.time() - self.start_time_second_batch
            benchmark_result_string = \
                f'Mean time per request: {round(duration/self.num_finished_jobs, 1)}s | ' \
                f'{round((self.num_finished_jobs - self.num_jobs_first_batch) * self.num_generated_units / duration, 1)} {self.unit}/s'
            return benchmark_result_string

    def remove_progress_bar(self, job_id):
        """Removing the progress bar of finished jobs with the given job id.

        Args:
            job_id (str): Job ID of the related job
        """        
        current_progress_bar = self.progress_bar_dict.get(job_id)     
        if current_progress_bar:
            current_position = current_progress_bar.pos
            current_progress_bar.close()
            del self.progress_bar_dict[job_id]
            self.remove_empty_line(current_position)


    def remove_empty_line(self, position):
        """Shifting all progress bars below the given position up by one position to remove empty lines of finished jobs.

        Args:
            position (int): Position
        """        
        for progress_bar in self.progress_bar_dict.values():
            if progress_bar.pos > position:
                current_position = progress_bar.pos
                progress_bar.clear(nolock=False)
                progress_bar.pos = current_position -1


    def print_start_message(self):
        """Printing benchmark parameters at the start.
        """        
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
        """Parsing the default job parameters from the related endpoint config file.

        Returns:
            dict: Job parameters for API request.
        """
        try:
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
            if params.get('num_samples'):
                params['num_samples'] = self.args.num_units
            return params

        except FileNotFoundError:
            params = input('No config file found. Type the input params in json:')
            return json.loads(params)
        

    async def do_request_with_semaphore(self):
        """Limiting the concurrent requests using asyncio.Semaphore().
        """
        async with self.semaphore:
            await self.model_api.do_api_request_async(
                self.params,
                self.result_callback,
                self.progress_callback,
                self.request_error_callback
                )


    def get_loop(self):
        """Getting either the running loop or create a new one if there is none.

        Returns:
            asyncio.unix_events._UnixSelectorEventLoop: The event loop handling asynchronous processes.
        """        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop


    def process_meta_data(self, result):
        """Parsing the job result for information about the API server and the workers.

        Args:
            result (dict): Job result
        """        
        self.endpoint_version = result.get('ep_version')
        self.model_name = result.get('model_name')
        self.worker_names.add(result.get('auth'))
        self.worker_interface_version = result.get('worker_interface_version')


    def get_unit(self):
        """Getting the unit of the generated objects like 'tokens' for llama2_chat and 'images' image generators.

        Returns:
            str: The unit string of the generated objects
        """
        if self.args.unit:
            return self.args.unit
        if self.args.endpoint_name == 'llama2_chat':
            return 'tokens'
        else:
            return 'images'


    async def request_error_callback(self, response):
        print(response)
        loop = self.get_loop()
        loop.stop()

def main():
    benchmark_api = BenchmarkApiEndpoint()
    benchmark_api.run()


if __name__ == "__main__":
	main()

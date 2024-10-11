# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from aime_api_client_interface import ModelAPI
import toml
import asyncio
import argparse
import time
from tqdm.auto import tqdm
from collections import Counter
import json
import math
import statistics
import re
import sys
import os


if os.name == 'nt':
    try:
        import msvcrt
        import ctypes
        HIDE_CURSOR = True
        class _CursorInfo(ctypes.Structure):
            _fields_ = [("size", ctypes.c_int),
                        ("visible", ctypes.c_byte)]
    except ModuleNotFoundError:
        HIDE_CURSOR = False
else:
    HIDE_CURSOR = True


HEADER_HEIGHT = 13
WIDTH_COLUMN_JOB_ID = 10

RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

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
        self.loop = asyncio.new_event_loop()
        self.semaphore = asyncio.Semaphore(self.args.concurrent_requests)
        self.title_bar_list = [tqdm(total=0, bar_format='{desc}', leave=False, position=i, colour='red', dynamic_ncols=True) for i in range(HEADER_HEIGHT)]
        self.unit, _, _ = self.get_unit(self.args)
        self.progress_bars = ProgressBarHandler(self.args, self.title_bar_list)
        self.jobs = JobHandler(self.args)
        self.durations_from_server = list()
        self.mean_duration_from_server = 0
        self.mean_rate_from_server = 0
        self.mean_time_per_request = 0
        self.mean_rate = 0
        self.start_time = None
        self.start_time_second_batch = None
        self.first_batch = True
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
            '-cr', '--concurrent_requests', type=int, default=40, required=False, 
            help='Number of concurrent asynchronous requests limited with asyncio.Semaphore().' \
                 'Choose at least twice the global batch size of all workers, to have full batches.'
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
        parser.add_argument(
            '-cff', '--context_from_file', type=str, required=False, help="Load context from text file"
        )
        parser.add_argument(
            '-nw', '--no_warmup', action='store_true', required=False, help="If not set, the first batch doesn't count for benchmark result."
        )
        args = parser.parse_args()
        if not args.config_file:
            if args.endpoint_name == 'sdxl_txt2img':
                args.endpoint_name = 'stable_diffusion_xl_txt2img'
            elif args.endpoint_name == 'stable_diffusion_xl_txt2img':
                args.config_file = 'endpoints/stable_diffusion_xl/txt2img/aime_api_endpoint.cfg'
            elif args.endpoint_name == 'llama2_chat' and args.num_units == 1:
                args.num_units = args.max_gen_len
                args.config_file = f'endpoints/{args.endpoint_name}/aime_api_endpoint.cfg'
            elif args.endpoint_name == 'llama3_chat'  and args.num_units == 1:
                args.num_units = 1024
                args.config_file = f'endpoints/{args.endpoint_name}/aime_api_endpoint.cfg'
            else:
                args.config_file = f'endpoints/{args.endpoint_name}/aime_api_endpoint.cfg'
                if not args.endpoint_name == 'stable_diffusion_3' and args.num_units == 1:
                    args.num_units = 500
        return args

    
    def run(self):
        """Starting the benchmark.
        """
        self.hide_cursor()
        self.print_start_message()
        self.update_worker_and_endpoint_data_in_title()
        _ = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=self.loop) for _ in range(self.args.total_requests)]
        self.loop.run_forever()


    async def progress_callback(self, progress_info, progress_data):
        """Called when job progress is received from the API Server. Initializes or updates the job related progress bar, 
        updates the title and measures the number of current running jobs.

        Args:
            progress_info (dict): Job progress information containing the job_id and the progress state like number of generated tokens so far or percentage.
            progress_data (dict): The already generated content like tokens or interim images.
        """
        job_id = progress_info.get('job_id')
        await self.handle_first_batch(progress_info)
        if not self.progress_bars.get(job_id) and progress_info.get('queue_position') == 0:
            self.progress_bars.new(job_id)
        
        self.progress_bars.update(progress_info)
        self.jobs.update(self.progress_bars.current_jobs)
        self.update_title()
        
        

    async def result_callback(self, result):
        """Called when the final job result is received. Removes the job related progress bar, processes information 
        about the server and the worker and updates the title.

        Args:
            result (dict): The final job result like a generated text, audio or images.
        """
        if result.get('success'):
            self.progress_bars.remove(result.get('job_id'))
            if self.first_batch: # If result_callback of first batch is called before progress_callback of second batch
                self.first_batch = False
                self.start_time_second_batch = time.time()
            if result.get('num_generated_tokens'):
                self.progress_bars.num_generated_units = result.get('num_generated_tokens')
            self.jobs.num_finished += 1
            self.update_mean_rate_and_time_per_request(result)
            self.update_title(result)
            
            if self.jobs.final_job_finished:
                self.print_benchmark_summary_string()
                self.show_cursor()
                await self.model_api.close_session()
                self.loop.stop()
        else:
            print(result)
            self.show_cursor()
            self.loop.stop()
            await self.model_api.close_session()


    def print_benchmark_summary_string(self):
        """Printing the benchmark summary and the results.
        """
        for title_bar in self.title_bar_list:
            title_bar.close()
        print(
            '\n---------------------------------',
            'Finished',
            '---------------------------------\n',
            'Result:',
            f'Number of jobs in first batch: {self.jobs.num_first_batch}',
            f'Estimated global batchsize of all workers: {self.jobs.max_num_running}',
            f'Number of generated {self.unit} per job: {self.progress_bars.num_generated_units}',
            *self.get_worker_and_endpoint_descriptions(),
            f'{self.args.total_requests} requests with maximum {self.args.concurrent_requests} concurrent requests took {tqdm.format_interval(time.time() - self.start_time_second_batch)}.',
            self.make_server_benchmark_string(True),
            self.make_benchmark_result_string(),
            sep='\n'
        )


    async def handle_first_batch(self, progress_info):
        """Detecting the jobs of the first batch to exclude them from the benchmark results.

        Args:
            progress_info (dict): Job progress information containing the job_id and the progress state like number of generated tokens so far or percentage.
        """        
        job_id = progress_info.get('job_id')
        if self.start_time:
            if (time.time() - self.start_time) <= self.args.time_to_get_first_batch_jobs:
                if self.first_batch:
                    self.jobs.collect_first_batch_jobs(self.progress_bars.current_jobs)                  
                else:
                    for progress_bar in self.progress_bars.current_jobs.values():
                        progress_bar.close()
                    self.title_bar_list[6].close()
                    self.title_bar_list[8].close()
                    self.loop.stop()
                    print('\n\n\n\n\n\n\nFirst batch finished before --time_to_get_first_batch_jobs. Choose a shorter time via command line argument!')
            else:
                if not self.first_batch_jobs_added:
                    _ = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=self.loop) for _ in range(self.jobs.num_first_batch)]
                    self.first_batch_jobs_added = True
                if self.first_batch and progress_info.get('progress') and job_id not in self.jobs.first_batch_job_dict.keys(): # If progress_callback of second batch is called before result_callback of first batch
                    self.first_batch = False
                    self.start_time_second_batch = time.time()
        elif progress_info.get('queue_position') == 0 and not self.start_time_second_batch:
            if self.args.no_warmup:
                self.first_batch = False
                self.start_time_second_batch = time.time()
            else:
                self.start_time = time.time()
            


    def update_title(self, result=None):
        """Updating the title bars for the header containing information about the benchmark.
        """
        title_lines = list()
        if result:
            self.update_worker_and_endpoint_data_in_title(result)
        if not self.start_time and not self.start_time_second_batch:
            title_lines.append(self.coloured_output('Waiting for available workers...', YELLOW))
        elif self.first_batch:
            first_line = self.coloured_output(f'Processing first batch for warmup! Results not taken into account for benchmark!', YELLOW)
            if self.jobs.num_first_batch:
                first_line += self.coloured_output(' Jobs in first batch: ', YELLOW) + self.coloured_output(self.jobs.num_first_batch, GREEN)
            title_lines.append(first_line)
            if self.first_batch_jobs_added:
                title_lines.append(
                    self.coloured_output(f'{self.args.time_to_get_first_batch_jobs}s have passed and first batch jobs are added.', YELLOW)
                )
            else:
                title_lines.append('')
            remaining_jobs = f'{self.coloured_output(self.jobs.num_first_batch, GREEN)} + {self.args.total_requests - self.jobs.num_finished} / {self.args.total_requests}'
            line = f'Remaining jobs: {remaining_jobs} | Current running jobs: {self.coloured_output(self.jobs.num_running, GREEN)}'
            if self.jobs.max_num_running:
                line += f' | Maximum running jobs: {self.jobs.max_num_running}'
            title_lines.append(line)
        else:
            
            line = f'Warmup stage with first batch containing {self.jobs.num_first_batch} jobs finished. ' if not self.args.no_warmup else 'No warmup batch! '
            line += f'Benchmark running for {tqdm.format_interval(time.time() - self.start_time_second_batch)}'
            title_lines.append(line)

            remaining_jobs = f'{self.jobs.num_first_batch + self.args.total_requests - self.jobs.num_finished} / {self.args.total_requests}'
            line = f'Remaining jobs: {self.coloured_output(remaining_jobs, GREEN)} | Current running jobs: {self.coloured_output(self.jobs.num_running, GREEN)}'
            if self.jobs.max_num_running:
                line += f' | Maximum running jobs: {self.jobs.max_num_running}'
            title_lines.append(line)
            title_lines.append(self.make_server_benchmark_string())
        title_lines.append(self.make_benchmark_result_string())
        title_lines.append('')
        
        for idx, line in enumerate(title_lines, start=6):
            screen_width = self.title_bar_list[idx].ncols
            self.title_bar_list[idx].set_description_str(f'{self.cut_colored_string(line, screen_width):<{screen_width}}')
            self.title_bar_list[idx].refresh()


    def update_worker_and_endpoint_data_in_title(self, result={}):
        """Updating the title bars with information about the API server and the workers.
        """
        self.endpoint_version = result.get('ep_version')
        self.model_name = result.get('model_name')
        if result.get('auth'):
            self.worker_names.add(result.get('auth'))
        self.worker_interface_version = result.get('worker_interface_version')

        descriptions = self.get_worker_and_endpoint_descriptions()
        for idx, line in enumerate(descriptions):
            screen_width = self.title_bar_list[idx].ncols
            self.title_bar_list[idx].set_description_str(f'{line[:screen_width]:<{screen_width}}' if line else line)
            self.title_bar_list[idx].refresh()
    

    def get_worker_and_endpoint_descriptions(self):
        unavailable = 'Available after first batch...' if self.first_batch else 'Missing! Maybe provide_worker_meta_data is set to False in endpoint config file'
        return [
            f'Number of detected workers: {len(self.worker_names) if self.worker_names else unavailable}',
            f'Worker names: {", ".join(self.worker_names) if self.worker_names else unavailable}',
            f'Worker Interface version: {self.worker_interface_version if self.worker_interface_version else unavailable}',
            f'Endpoint version: {self.endpoint_version if self.endpoint_version else unavailable}',
            f'Model name: {self.model_name if self.model_name else unavailable}'
        ]


    def update_mean_rate_and_time_per_request(self, result):

        if self.jobs.num_finished > self.jobs.num_first_batch:
            self.mean_time_per_request = (time.time() - self.start_time_second_batch)/(self.jobs.num_finished - self.jobs.num_first_batch)
            self.mean_rate = (self.jobs.num_finished - self.jobs.num_first_batch) * self.progress_bars.num_generated_units / (time.time() - self.start_time_second_batch)
        else:
            self.mean_time_per_request = (time.time() - self.start_time)/(self.jobs.num_finished)
            self.mean_rate = self.jobs.num_finished * self.progress_bars.num_generated_units / (time.time() - self.start_time)
        if result.get('compute_duration'):
            self.durations_from_server.append(result.get('compute_duration'))
            self.mean_duration_from_server = statistics.mean(self.durations_from_server)
            self.mean_rate_from_server = self.progress_bars.num_generated_units / self.mean_duration_from_server
        if self.jobs.num_finished == self.jobs.num_first_batch:
            self.durations_from_server.clear()
        

    def make_benchmark_result_string(self):
        """Making string containing mean benchmark results.

        Returns:
            str: Result string
        """
        result_string_list = list()
        if self.mean_time_per_request:
            result_string_list.append(
                'Mean time per request: ' + self.coloured_output(f'{tqdm.format_sizeof(self.mean_time_per_request)}s', GREEN)
            )
        if self.mean_rate:
            result_string_list.append(
                'Mean rate: ' + self.coloured_output(f'{tqdm.format_sizeof(self.mean_rate)} {self.unit}/s', GREEN)
            )
        if not (self.jobs.num_finished - self.jobs.num_first_batch) == self.args.total_requests:
            current_rate = self.progress_bars.get_current_rate_total()
            if current_rate:
                result_string_list.append(
                    'Current rate: ' + self.coloured_output(f'{tqdm.format_sizeof(current_rate)} {self.unit}/s', GREEN)
                )
        return ' | '.join(result_string_list)


    def make_server_benchmark_string(self, final=False):
        if self.mean_rate_from_server:
            num_running_jobs = self.jobs.max_num_running if final else self.jobs.num_running
            return 'From ' + self.coloured_output('Server', YELLOW) + \
                ': Mean duration per job: ' + self.coloured_output(f'{tqdm.format_sizeof(self.mean_duration_from_server)}s', YELLOW) + \
                ' | Mean rate per user: ' + self.coloured_output(f'{tqdm.format_sizeof(self.mean_rate_from_server)} {self.unit}/s', YELLOW) + \
                ' | Mean rate: ' + self.coloured_output(f'{tqdm.format_sizeof(self.mean_rate_from_server * num_running_jobs)} {self.unit}/s', YELLOW)
            

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
        if sys.version_info < (3, 10):
            print(self.coloured_output(f'WARNING! You are running python version {sys.version}. High numbers of --total_requests are supported only from Python version 3.10 onwards', YELLOW))
        else:
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
                if ep_inputs[ep_input].get('required') or ep_inputs[ep_input].get('default') is not None:
                    params[ep_input] = ep_inputs[ep_input].get('default')
            if params.get('seed'):
                params['seed'] = 1
            if params.get('top_k'):
                params['top_k'] = 1
                params['top_p'] = 1
            if params.get('num_samples'):
                params['num_samples'] = self.args.num_units
            if params.get('max_gen_tokens'):
                params['max_gen_tokens'] = self.args.num_units
            if params.get('text'):
                if self.args.context_from_file:
                    with open(self.args.context_from_file, 'r', encoding='latin-1') as file:
                        params['text'] = file.read()
                else:
                    params['text'] = 'Tell a long story: Once upon a time'
            if params.get('prompt_input') is not None:
                if self.args.context_from_file:
                    with open(self.args.context_from_file, 'r', encoding='latin-1') as file:
                        params['prompt_input'] = file.read() 
                else:
                    params['prompt_input'] = 'Tell a very long story with at least 500 words: Once upon a time'

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

    @staticmethod
    def get_unit(args):
        """Getting the unit of the generated objects like 'tokens' for llama2_chat and 'images' image generators.

        Returns:
            str: The unit string of the generated objects
        """
        if args.endpoint_name in ['llama2_chat', 'llama3_chat', 'mixtral_chat']:
            return 'tokens', 1, 0    
        else:
            if args.unit:
                unit = args.unit
            else:
                unit = 'images'
            if args.num_units < 10:
                unit_precision = 2
            elif 10 <= args.num_units:
                unit_precision = 1
            else:
                unit_precision = 0
            return unit, args.num_units/100, unit_precision


    @staticmethod
    def coloured_output(string, colour_tag):
        return colour_tag + str(string) + RESET


    @staticmethod
    def cut_colored_string(input_string, max_length):
        color_pattern = re.compile(r'\033(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output = ''
        if input_string:
            segments = input_string.split(RESET)
            sorted_segments = []
            for segment in segments:
                sub_segment = color_pattern.split(segment)
                if color_pattern.findall(segment):
                    sub_segment.insert(1, *color_pattern.findall(segment))
                    sub_segment.append(RESET)
                sorted_segments += sub_segment
            current_length = 0
            for segment in sorted_segments:
                if color_pattern.match(segment):
                    output += segment
                else:
                    segment_length = len(segment)
                    if current_length + segment_length <= max_length:
                        output += segment
                        current_length += segment_length
                    else:
                        remaining_length = max_length - current_length
                        output += segment[:remaining_length] + RESET
                        break
        return output


    async def request_error_callback(self, response):
        print(response)
        self.show_cursor()
        self.loop.stop()

    
    def hide_cursor(self):
        if HIDE_CURSOR:
            if os.name == 'nt':
                ci = _CursorInfo()
                handle = ctypes.windll.kernel32.GetStdHandle(-11)
                ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
                ci.visible = False
                ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
            elif os.name == 'posix':
                sys.stdout.write("\033[?25l")
                sys.stdout.flush()


    def show_cursor(self):
        if HIDE_CURSOR:
            if os.name == 'nt':
                ci = _CursorInfo()
                handle = ctypes.windll.kernel32.GetStdHandle(-11)
                ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
                ci.visible = True
                ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
            elif os.name == 'posix':
                sys.stdout.write("\033[?25h")
                sys.stdout.flush()



class ProgressBarHandler():

    def __init__(self, args, title_bar_list):
        self.args = args
        self.title_bar_list = title_bar_list
        self.num_generated_units = self.args.num_units
        self.positions = PositionHandler()
        self.current_jobs = dict()
        self.last_progress_dict = dict()
        self.current_rate_dict = dict()
        self.unit, self.unit_scale, self.unit_precision = BenchmarkApiEndpoint.get_unit(self.args)

    def new(self, job_id):
        """Initializing the progress bar of the job with the given job ID.

        Args:
            job_id (str): Job ID of the related job
        """
        self.current_jobs[job_id] = tqdm(
            total = self.num_generated_units, # the unit_scale arg in tqdm shows wrong rate for sdxl
            unit=' ' + self.unit,
            position = self.positions.new(job_id),
            desc=f'{job_id[:WIDTH_COLUMN_JOB_ID]:<{WIDTH_COLUMN_JOB_ID}}',
            leave=False,
            bar_format=f'{{desc}} | {{percentage:3.0f}}% {{bar}}| {{n:.{self.unit_precision}f}} / {{total:.{self.unit_precision}f}} |   {{elapsed}} < {{remaining}}  | ' '{rate_noinv_fmt} {postfix}',
            dynamic_ncols=True,
            colour='blue'
            )


    def get(self, job_id):
        return self.current_jobs.get(job_id)


    def update(self, progress_info):
        """Updating the related progress bar with the given progress state.

        Args:
            progress_info (dict): Job progress information containing the job_id and the progress state like number of generated tokens so far or percentage.
        """
        job_id = progress_info.get('job_id')
        
        current_progress_bar = self.current_jobs.get(job_id)
        if current_progress_bar:
            self.positions.update(self.current_jobs)
            current_progress = progress_info.get('progress')
            if self.args.endpoint_name in ['llama2_chat', 'llama3_chat', 'mixtral_chat']:
                if self.num_generated_units < current_progress:
                    current_progress_bar.total = current_progress
                else:
                    current_progress_bar.total = self.num_generated_units
            current_progress_bar.n = current_progress * self.unit_scale
            if self.positions.get(job_id) == HEADER_HEIGHT:
                self.update_table_title(current_progress)
            self.measure_current_rate(progress_info)
            current_progress_bar.refresh()


    def remove(self, job_id):
        """Removing the progress bar of finished jobs with the given job id.

        Args:
            job_id (str): Job ID of the related job
        """
        self.positions.release(job_id)
        current_progress_bar = self.current_jobs.get(job_id)     
        if current_progress_bar:
            current_progress_bar.close()
            del self.current_jobs[job_id]
            del self.current_rate_dict[job_id]
            del self.last_progress_dict[job_id]


    def update_table_title(self, current_progress):
        """Setting the column descriptions and adjusting the position of the table title bar for the progress bar table.
        """
        if self.current_rate_dict:
            rate = [element for element in self.current_rate_dict.values()][0]
        else:
            rate = 0
        screen_width = self.title_bar_list[HEADER_HEIGHT-2].ncols
        
        
        column_title_job_id = 'JOB ID'
        column_title_job_id += ' ' * (WIDTH_COLUMN_JOB_ID - len(column_title_job_id))
        
        column_title_progress_unit = f'| {self.unit}'
        column_title_progress_unit += ' ' * (
            len(f'| {(current_progress * self.unit_scale):.{self.unit_precision}f} / {self.num_generated_units:.{self.unit_precision}f}') - len(column_title_progress_unit)
        )
        column_title_duration = ' | Elapsed < Remain | '
        column_title_benchmark = 'Benchmark'
        column_title_benchmark += ' ' * (len(f' {tqdm.format_sizeof(rate)} {self.unit}/s ') - len(column_title_benchmark))
        right_bar = column_title_progress_unit + column_title_duration + column_title_benchmark
        length_progress_bar = max(screen_width - len(column_title_job_id + right_bar), 9)
        column_title_progress_percentage = f'{" | Progress in percentage"[:length_progress_bar]:<{length_progress_bar}}'
        title_str = column_title_job_id + column_title_progress_percentage + right_bar
        self.title_bar_list[HEADER_HEIGHT-2].set_description_str(title_str[:screen_width])
        self.title_bar_list[HEADER_HEIGHT-1].set_description_str('-' * screen_width)


    def measure_current_rate(self, progress_info):
        job_id = progress_info.get('job_id')
        current_progress = progress_info.get('progress')
        tic = time.time()
        last_progress, time_last_progress = self.last_progress_dict.get(job_id, (None, None))
        if last_progress:
            if ((tic - time_last_progress) > 1):
                if self.current_rate_dict.get(job_id):
                    self.current_rate_dict[job_id] = 0.8 * self.current_rate_dict[job_id] + 0.2 * ((current_progress - last_progress) * self.unit_scale / (tic - time_last_progress))
                else:
                    self.current_rate_dict[job_id] = (current_progress - last_progress) * self.unit_scale / (tic - time_last_progress) 
                
                self.last_progress_dict[job_id] = current_progress, tic
            else:
                self.last_progress_dict[job_id] = last_progress, time_last_progress
        else:
            self.last_progress_dict[job_id] = current_progress, tic


    def get_current_rate_total(self):
        return sum(self.current_rate_dict.values())



class PositionHandler():

    def __init__(self):
        self._counter = HEADER_HEIGHT - 1
        self.vacant = list()
        self.running_jobs = dict()


    def new(self, job_id):
        if self.vacant:
            position = self.vacant.pop()
        else:
            self._counter += 1
            position = self._counter
        self.running_jobs[job_id] = position
        return position


    def get(self, job_id):
        return self.running_jobs.get(job_id)

    def set_position(self, current_position, target_position, job_id, progress_bar_dict):
        current_progress_bar = progress_bar_dict.get(job_id)
        current_progress_bar.clear()
        current_progress_bar.pos = target_position
        self.running_jobs[job_id] = target_position
        self.vacant.remove(target_position)
        self.vacant.append(current_position)

    def update(self, progress_bar_dict):
        if self.vacant and min(self.vacant) < max(self.running_jobs.values()):
            running_jobs = self.running_jobs.copy()
            for job_id, position in sorted(running_jobs.items()):
                min_vacant = min(self.vacant)
                if position > min_vacant:
                    self.set_position(position, min_vacant, job_id, progress_bar_dict)

    def release(self, job_id):
        self.vacant.append(self.get(job_id))
        del self.running_jobs[job_id]


class JobHandler():

    def __init__(self, args):
        self.args = args
        self.num_running = 0
        self.last_update_time = time.time()
        self.last_update_num_running = 0
        self.max_num_running = 0
        self.num_finished = 0
        self.first_batch_job_dict = dict()
        self.num_first_batch = 0


    @property
    def final_job_finished(self):
        return self.num_finished == self.args.total_requests + self.num_first_batch


    def update(self, progress_bar_dict):
        self.num_running = sum([1 for progress_bar in progress_bar_dict.values() if 0 < progress_bar.n])
        if (time.time() - self.last_update_time) > 1:
            self.last_update_time = time.time()
            if self.last_update_num_running == self.num_running:
                self.max_num_running = self.num_running
            self.last_update_num_running = self.num_running


    def collect_first_batch_jobs(self, progress_bar_dict):
        if self.num_first_batch < self.num_running:
            self.first_batch_job_dict = {job_id: progress_bar for job_id, progress_bar in progress_bar_dict.items() if progress_bar.n}
            self.num_first_batch = self.num_running


def main():
    
        benchmark_api = BenchmarkApiEndpoint()
        try:
            benchmark_api.run()
        except KeyboardInterrupt:
            
            for title_bar in benchmark_api.title_bar_list:
                title_bar.clear()
            for progress_bar in benchmark_api.progress_bars.current_jobs.values():
                progress_bar.clear()
            benchmark_api.show_cursor()
            print('\nKeyboardInterrupt')
            if not benchmark_api.first_batch:
                benchmark_api.print_benchmark_summary_string()


if __name__ == "__main__":
	main()

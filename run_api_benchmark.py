# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from aime_api_client_interface import ModelAPI
import toml
import asyncio
import argparse
import time
from datetime import datetime
from tqdm.auto import tqdm
from collections import Counter
import json
import math
import statistics
import re
import sys
import os
from pathlib import Path
import requests
import aiofiles


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


WIDTH_COLUMN_JOB_ID = 10

RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
ORANGE = '\033[38;5;202m'
RESET = '\033[0m'

RATE_TYPES = [
    'total_job',
    'worker_compute',
    'worker_preprocessing',
    'worker_generation',
    'compute_from_server',
    'total_from_server',
    'transfer_client2server',
    'transfer_server2worker',
    'transfer_worker2server',
    'transfer_server2client'
]

PROMPT_TEMPLATES = {
    '2K': '2K_tokens_adventures_of_huckleberry_finn_chapter_I_1400_words',
    '4K': '4K_tokens_hansel_and_gretel_3K_words',
    '8K': '8K_tokens_war_of_worlds_chapter_I-IV_6K_words',
    '16K': '16K_tokens_peter_pan_chapter_I-III_10K_words',
    '32K': '32K_tokens_alices_adventures_in_wonderland_chapter_I-IX_20K_words',
    '128K': '128K_tokens_frankenstein_78K_words'
}

class BenchmarkApiEndpoint():
    """Benchmark tool to measure and monitor the performance of GPUs with multiple asynchronous requests on chat and stable_diffusion_xl_txt2img endpoints.
    """    

    def __init__(self):
        
        self.args = self.load_flags()
        self.model_api = ModelAPI(
            self.args.api_server,
            self.args.endpoint_name,
            self.args.user_name,
            self.args.login_key
        )
        try:
            self.model_api.do_api_login()
        except ConnectionError as error:
            exit(error)
        self.params = self.get_job_parameter()

        self.loop = asyncio.new_event_loop()
        self.lock = asyncio.Lock()
        self.error_event = asyncio.Event()
        self.error = None
        self.all_jobs_done_event = asyncio.Event()
        self.semaphore = asyncio.Semaphore(self.args.concurrent_requests)

        self.start_time = None
        self.start_time_second_batch = None
        self.first_batch = True
        self.jobs = JobHandler(self.args, self.lock)

        self.worker_names = set()
        self.endpoint_version = int()
        self.model_name = str()
        self.worker_interface_version = str()
        self.print_start_message()
        
        self.header = self.init_header()
        self.unit, _, _ = self.get_unit(self.args)
        self.progress_bars = ProgressBarHandler(self.args, self.header_height, self.lock)      
        
        self.first_batch_jobs_added = False
        self.request_id = 0
        self.registered_jobs = list()
        self.last_update = dict()


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
            '-tr', '--total_requests', type=int, default=4, required=False, help='Total number of requests. Choose a multiple of the worker\'s batchsize to have a full last batch'
        )
        parser.add_argument(
            '-cr', '--concurrent_requests', type=int, default=40, required=False, 
            help='Number of concurrent asynchronous requests limited with asyncio.Semaphore().' \
                 'With serially processing workers choose at least twice the global batch size of all workers, to have full batches.'
        )
        parser.add_argument(
            '-cf', '--config_file', type=str, required=False, help='To change address of endpoint config file to get the default values of the job parameters'
        )
        parser.add_argument(
            '-ep', '--endpoint_name', type=str, default='llama3_chat', required=False, help='Name of the endpoint'
        )
        parser.add_argument(
            '-ut', '--unit', type=str, required=False, help='Unit of the generated objects. Default: "tokens" if endpoint_name contains "chat" else  "images"'
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
            '-ml', '--max_tok_len', default=1024, type=int, required=False, help='Maximum length showed in the first batch.'
        )
        parser.add_argument(
            '-i', '--prompt_input_from_files', type=str, required=False, help='Load prompt input from text files.'
        )
        parser.add_argument(
            '-nw', '--no_warmup', action='store_true', required=False, help='If not set, the first batch doesn\'t count for benchmark result.'
        )
        parser.add_argument(
            '-lf', '--log_file', type=str, required=False, help='Add results to given log file. Generates it if not existing.'
        )
        parser.add_argument(
            '-js', '--json', type=str, required=False, help='Write benchmark result in given json File.'
        )
        parser.add_argument(
            '-pt', '--prompt_template', choices=['2K', '4K', '8K', '16K', '32K', '128K'], help='Download long prompt approximately containing the given number of tokens from AIME'
        )
        parser.add_argument(
            '-dev', '--debug', action='store_true', help='Write debug logs in debug_log.txt.'
        )
        parser.add_argument(
            '-sw', '--serial_processing_worker', action='store_true', help='If the worker processes requests only serially.'
        )
        parser.add_argument(
            '-r', '--resolution', type=str, required=False, help='For Image Generators like SD: The target resolution of the generated image. Format: <width>x<height>'
        )
        
        args = parser.parse_args()
        if not args.config_file:
            endpoint_dir = Path(__file__).resolve().parent / 'endpoints'
            if args.endpoint_name == 'sdxl_txt2img':
                args.endpoint_name = 'stable_diffusion_xl_txt2img'
                args.config_file = endpoint_dir / args.endpoint_name / 'aime_api_endpoint.cfg'
            elif args.endpoint_name == 'stable_diffusion_xl_txt2img':
                args.config_file = endpoint_dir / 'stable_diffusion_xl' / 'txt2img' / 'aime_api_endpoint.cfg'
            else:
                args.config_file = endpoint_dir / args.endpoint_name / 'aime_api_endpoint.cfg'
                if 'chat' in args.endpoint_name and args.num_units == 1:
                    args.num_units = 1024
        return args

    
    def run(self):
        """Starting the benchmark.
        """
        self.hide_cursor()
        asyncio.ensure_future(self.run_all_jobs(), loop=self.loop)
        self.loop.run_forever()


    async def run_all_jobs(self):
        _ = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=self.loop) for _ in range(self.args.total_requests)]
        await self.all_jobs_done_event.wait() 
        await self.finish_benchmark()


    async def process_progress_result(self, result):
        """Called when job progress is received from the API Server. Initializes or updates the job related progress bar, 
        updates the title and measures the number of current running jobs.

        Args:
            progress_info (dict): Job progress information containing the job_id and the progress state like number of generated tokens so far or percentage.
            progress_data (dict): The already generated content like tokens or interim images.
        """
        if not self.error_event.is_set():
            job_id = result.get('job_id')
            await self.handle_first_batch(result)
            await self.update_header()
            if not self.progress_bars.get(job_id) and result.get('queue_position') == 0:
                await self.progress_bars.new(job_id, self.header_height)
            
            await self.progress_bars.update(result, self.header_height)
            await self.jobs.update(self.progress_bars.current_jobs)
        

    async def process_job_result(self, result):
        """Called when the final job result is received. Removes the job related progress bar, processes information 
        about the server and the worker and updates the title.

        Args:
            result (dict): The final job result like a generated text, audio or images.
        """
        result_received_time = time.time()

        if result.get('success'):
            result_data = result.get('result_data', {})
            if result_data:
                if not result_data.get('error'):
                    await self.progress_bars.remove(result.get('job_id'))
                    if self.first_batch: # If job result of first batch arrived before progress result of second batch
                        self.first_batch = False
                        self.start_time_second_batch = result_received_time
                    if result_data.get('num_generated_tokens'):
                        self.progress_bars.num_generated_units = result_data.get('num_generated_tokens')
                    await self.jobs.finish(
                        result_data,
                        finish_time=result_received_time
                    )
                    await self.update_header(result_data)
                else:
                    self.error = result_data.get('error')
                    self.error_event.set()
            else:
                print(result)
                self.error = f'No result data in result: {result}'
                self.error_event.set()
        else:
            self.error = result.get('error')
            self.error_event.set()


    async def finish_benchmark(self):
        """Printing the benchmark summary and the results.
        """
        for title_bar in self.progress_bars.title_bar_list:
            title_bar.refresh()
            title_bar.close()
        for header_line in self.header:
            header_line.refresh()
            header_line.close()
        for progress_bar in self.progress_bars.current_jobs.values():
            progress_bar.clear()
        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        if self.args.json:
            self.make_json_output(now)
        if self.error:
            summary_string = f'\nError: {self.error}'
        else:
            result_table = self.make_benchmark_result_table(final=True)
            time_string = f'Benchmark finished at {now}'         
            warning_str = self.coloured_output(
                f'Attention: Concurrent request = {self.args.concurrent_requests} is not equal to the actual batch size of the worker {self.jobs.max_num_running}', YELLOW
                ) if self.args.concurrent_requests != self.jobs.max_num_running and not self.args.serial_processing_worker else ''
            summary_string = '\n'.join((
                '-' * len(time_string),
                time_string,
                '-' * len(time_string) + '\n',
                'Result:',
                f'Number of jobs in first batch: {self.jobs.num_first_batch}' if not self.args.no_warmup else '',
                f'Estimated global batchsize of all workers: {self.jobs.max_num_running}',
                f'Number of generated {self.unit} per job: {self.progress_bars.num_generated_units}',
                *self.get_worker_and_endpoint_descriptions(),
                f'{self.args.total_requests} requests with maximum {self.args.concurrent_requests} concurrent requests took {tqdm.format_interval(time.time() - self.start_time_second_batch)}.',
                warning_str,
                *result_table 
            ))
        print(summary_string)
        self.show_cursor()
        self.add_to_logfile(summary_string)
        await self.close_all_tasks()     
        await self.model_api.close_session()
        self.loop.stop()
        


    def make_json_output(self, date_time):
        output_dict = {
            **self.params,
            'total_requests': self.args.total_requests,
            'concurrent_requests': self.args.concurrent_requests,
            'finish_time': date_time,
            'mean_durations': self.jobs.mean_durations,
            'mean_batch_rates': self.jobs.mean_batch_rates,
            'mean_single_rates': self.jobs.mean_single_rates,
            'num_jobs_first_batch': self.jobs.num_first_batch if not self.args.no_warmup else 0,
            'max_num_jobs_running': self.jobs.max_num_running,
            'num_units': self.progress_bars.num_generated_units,
            'prompt_template': self.args.prompt_template,
            'num_workers': len(self.worker_names) if self.worker_names else None,
            'Worker names': ', '.join(self.worker_names) if self.worker_names else None,
            'worker_interface_version': self.worker_interface_version or None,
            'endpoint_version': self.endpoint_version or None,
            'model_name': self.model_name or None,
            'error': str(self.error)
        }
        json_file = Path(self.args.json)
        if not json_file.parent.is_dir():
            json_file.parent.mkdir()
        with open(json_file, 'w') as file: 
            json.dump(output_dict, file)


    def add_to_logfile(self, content):
        if self.args.log_file:
            log_file = Path(self.args.log_file)
            if not log_file.parent.is_dir():
                log_file.parent.mkdir()
            with open(self.args.log_file, 'a') as f:
                f.write(content)


    async def close_all_tasks(self):
        pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
        pending_tasks.remove(asyncio.current_task())
        for task in pending_tasks:
            task.cancel()
        await asyncio.gather(*pending_tasks, return_exceptions=True)


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
                    self.show_cursor()
                    self.error = f'First batch finished before --time_to_get_first_batch_jobs = {self.args.time_to_get_first_batch_jobs}. Choose a shorter time via command line argument!'
                    self.error_event.set()
            else:
                await self.handle_first_batch_jobs()
                if self.first_batch and progress_info.get('progress') and job_id not in self.jobs.first_batch_jobs.keys(): # If progress result of second batch arrived before job result of first batch
                    self.first_batch = False
                    self.start_time_second_batch = time.time()

        elif progress_info.get('queue_position') == 0 and not self.start_time_second_batch:
            if self.args.no_warmup:
                self.first_batch = False
                self.start_time_second_batch = time.time()
            else:
                self.start_time = time.time()

    async def handle_first_batch_jobs(self):
        async with self.lock:
            if not self.first_batch_jobs_added:
                _ = [asyncio.ensure_future(self.do_request_with_semaphore(), loop=self.loop) for _ in range(self.jobs.num_first_batch)]
                self.first_batch_jobs_added = True

    def init_header(self):
        header = self.get_worker_and_endpoint_descriptions()
        header.extend(['', ''])
        return [
            tqdm(
                total=0,
                bar_format='{desc}',
                desc=line,
                leave=False,
                position=idx,
                dynamic_ncols=True
            ) for idx, line in enumerate(header)
        ]
        
    async def update_header(self, result={}, init=False):
        """Updating the title bars for the header containing information about the benchmark.
        """
        
        header = self.get_worker_and_endpoint_descriptions(result)
        header.append('')
        if not self.start_time and not self.start_time_second_batch:
            header.append(self.coloured_output('Waiting for available workers...', YELLOW))
        elif self.first_batch:
            first_line = self.coloured_output(f'Processing first batch for warmup! Results not taken into account for benchmark!', YELLOW)
            if self.jobs.num_first_batch:
                first_line += self.coloured_output(' Jobs in first batch: ', YELLOW) + self.coloured_output(self.jobs.num_first_batch, GREEN)
            header.append(first_line)
            if self.first_batch_jobs_added:
                header.append(
                    self.coloured_output(f'{self.args.time_to_get_first_batch_jobs}s have passed and first batch jobs are added.', YELLOW)
                )
            else:
                header.append('')
            remaining_jobs = f'{self.coloured_output(self.jobs.num_first_batch, GREEN)} + {self.args.total_requests - self.jobs.num_finished} / {self.args.total_requests}'
            line = f'Remaining jobs: {remaining_jobs} | Current running jobs: {self.coloured_output(self.jobs.num_running, GREEN)}'
            if self.jobs.max_num_running:
                line += f' | Maximum running jobs: {self.jobs.max_num_running}'
            header.append(line)
        else:
            
            line = f'Warmup stage with first batch containing {self.jobs.num_first_batch} jobs finished. ' if not self.args.no_warmup else 'No warmup batch! '
            line += f'Benchmark running for {tqdm.format_interval(time.time() - self.start_time_second_batch)}'

            header.append(line)

            remaining_jobs = f'{self.jobs.num_first_batch + self.args.total_requests - self.jobs.num_finished} / {self.args.total_requests}'
            line = f'Remaining jobs: {self.coloured_output(remaining_jobs, GREEN)} | Current running jobs: {self.coloured_output(self.jobs.num_running, GREEN)}'
            if self.jobs.max_num_running:
                line += f' | Maximum running jobs: {self.jobs.max_num_running}'
            header.append(line)
        header.append('')

             
        result_table = self.make_benchmark_result_table()
        if result_table:
            header += result_table
        async with self.lock:
            if len(header) != self.header_height:
                header_changed = True
                self.adjust_header(len(header))
            else:
                header_changed = False
            for idx, line in enumerate(header):
                screen_width = self.header[idx].ncols
                description = f'{self.align_coloured_string(line, screen_width)}'
                if self.header[idx].desc != description or header_changed:
                    self.header[idx].clear()
                    self.header[idx].set_description_str(description)
                    self.header[idx].refresh()


    def adjust_header(self, height):
        if height > self.header_height:
            self.header += [
                tqdm(
                    total=0,
                    bar_format='{desc}',
                    leave=False,
                    position=idx,
                    colour='red',
                    dynamic_ncols=True
                ) for idx in range(self.header_height, height)
            ]
        else:
            self.header = self.header[:height]
  

    def get_worker_and_endpoint_descriptions(self, result={}):
        
        unavailable = 'Available after first job result...' if not self.jobs.num_finished else 'Missing! Maybe provide_worker_meta_data is set to False in endpoint config file'
        self.endpoint_version = result.get('ep_version') or self.endpoint_version
        self.model_name = result.get('model_name') or self.model_name
        if result.get('auth'):
            self.worker_names.add(result.get('auth'))
        self.worker_interface_version = result.get('worker_interface_version') or self.worker_interface_version
        return [
            f'Number of detected workers: {len(self.worker_names) if self.worker_names else unavailable}',
            f'Worker names: {", ".join(self.worker_names) if self.worker_names else unavailable}',
            f'Worker Interface version: {self.worker_interface_version or unavailable}',
            f'Endpoint version: {self.endpoint_version or unavailable}',
            f'Model name: {self.model_name or unavailable}'
        ]
       

    def make_benchmark_result_table(self, final=False):
        mean_durations = self.jobs.mean_durations
        mean_batch_rates = self.jobs.mean_batch_rates
        mean_single_rates = self.jobs.mean_single_rates
        duration_column_title = 'Time (s)'
        rate_column_title = f'Rate ({self.unit}/s)'
        batch_rate_column_title = 'Total'
        rate_per_job_column_title = 'Single'
        rows = [('Total job', 'total_job', GREEN)]
        if final:
            rows += [
                (f'Total job in {self.coloured_output("server", YELLOW)}', 'total_from_server', YELLOW),
                (f'Compute in {self.coloured_output("server", YELLOW)}', 'compute_from_server', YELLOW)
            ]
        else:
            mean_batch_rates['current'] = self.progress_bars.get_current_rate_total()
            mean_single_rates['current'] = self.progress_bars.get_current_rate_single()
            rows.insert(0, ('Current', 'current', ORANGE))
        rows += [
            ('Total job in worker', 'worker_compute', GREEN),
            ('Generation in worker', 'worker_generation', GREEN),
            ('Preprocessing in worker', 'worker_preprocessing', GREEN),
        ]
        if final:
            rows += [         
                ('Transfer Client - Server', 'transfer_client2server', YELLOW),
                ('Transfer Server - Worker', 'transfer_server2worker', YELLOW),
                ('Transfer Worker - Server', 'transfer_worker2server', YELLOW),
                ('Transfer Server - Client', 'transfer_server2client', YELLOW),
                ('Pending in worker', 'worker_pending', GREEN),
                (f'Pending in {self.coloured_output("server", YELLOW)}', 'server_pending', YELLOW)
            ]          
        title_column_length = max(len(self.clean_ansi_string(row[0])) for row in rows)
        title_bar = f'{" ":{title_column_length}} | {duration_column_title} | {rate_column_title}'
        title_bar_2 = f'{" ":{title_column_length}} | {" ":{len(duration_column_title)}} | {batch_rate_column_title} | {rate_per_job_column_title}'
        result_table = [title_bar, title_bar_2, '-' * len(title_bar)]
        for label, key, color in rows:
            line = [
                f'{self.align_coloured_string(label, title_column_length)}',
                f'{self.format_benchmark_value(mean_durations.get(key, ""), len(duration_column_title), color)}',
                f'{self.format_benchmark_value(mean_batch_rates.get(key, ""), len(batch_rate_column_title), color)}',
                f'{self.format_benchmark_value(mean_single_rates.get(key, ""), len(rate_per_job_column_title), color)}'
            ]
            if len([value for value in line if value.strip()]) > 1:
                result_table.append(' | '.join(line))
        return result_table


    def format_benchmark_value(self, input_string, length, color=GREEN):
        try:
            return self.coloured_output(f'{tqdm.format_sizeof(input_string):>{length}}', color)
        except TypeError:
            return ' ' * length


    def print_start_message(self):
        """Printing benchmark parameters at the start.
        """
        start_message = \
            f'\nStarting Benchmark on {self.args.api_server}/{self.args.endpoint_name} with\n' +\
            f'{self.args.total_requests} total requests\n' +\
            f'{self.args.concurrent_requests} concurrent requests\n'
        start_message += f'Time after jobs in first batch got checked: {self.args.time_to_get_first_batch_jobs}s\n' if not self.args.no_warmup else ''
        start_message += f'Job parameters:\n'
        
        for key, value in self.params.items():
            if isinstance(value, str) and len(value) >= 40:
                value = value[:40].replace('\n', '') + '...'
            start_message += (f'{key}: {value}\n')

        if self.args.prompt_template:
            start_message += f'Prompt length in tokens: {self.args.prompt_template}\n'
        prompt = self.params.get("text") or self.params.get("prompt_input")
        if prompt:
            start_message += f'Number of characters in prompt: {len(prompt)}'
        print(start_message)
        self.add_to_logfile(start_message)
        if sys.version_info < (3, 10):
            print(self.coloured_output(f'WARNING! You are running python version {sys.version}. High numbers of --total_requests are supported only from Python version 3.10 onwards', YELLOW))
        else:
            print()


    def get_job_parameter(self):
        params = self.get_default_values_from_config()
        

        if params.get('seed'):
            params['seed'] = 1
        if params.get('top_k'):
            params['top_k'] = 1
            params['top_p'] = 1
        if params.get('num_samples'):
            params['num_samples'] = self.args.num_units
        if params.get('max_gen_tokens'):
            params['max_gen_tokens'] = self.args.num_units
        for prompt_key in ('text', 'prompt_input'):
            if params.get(prompt_key) is not None:
                if self.args.prompt_input_from_files:
                    params[prompt_key] = self.read_prompt_from_files()
                elif self.args.prompt_template:
                    response = requests.get(
                        f'https://www.aime.info/data/benchmark/llm/{PROMPT_TEMPLATES[self.args.prompt_template]}.txt'
                    )
                    if response.status_code == 200:
                        params[prompt_key] = response.text
                    else:
                        exit(f'--prompt_template is currently not working because https://www.aime.info/data/benchmark/llm/{PROMPT_TEMPLATES[self.args.prompt_template]}.txt is offline! ')
                else:
                    params[prompt_key] = 'Tell a very long story with at least 500 words: Once upon a time'
        if self.args.resolution:
            width, height = self.args.resolution.split('x')
            params['width'] = width
            params['height'] = height
        return params


    def read_prompt_from_files(self):

        input_path = Path(self.args.prompt_input_from_files)
        input_data = str()
        if input_path.is_file():
            with open(input_path, 'r', encoding='utf-8') as file:
                input_data = file.read()
        elif input_path.is_dir():
            for file_path in input_path.rglob("*.txt"):
                with open(file_path, 'r', encoding='utf-8') as file:
                    input_data += file.read()
        else:
            exit(f'Invalid input: {input_path}')
        return input_data


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
            return params

        except FileNotFoundError:
            params = input('No config file found. Type the input params in json:')
            return json.loads(params)


    async def do_request_with_semaphore(self):
        """Limiting the concurrent requests using asyncio.Semaphore().
        """
        async with self.semaphore:
            start_time = time.time()
            try:
                output_generator = self.model_api.get_api_request_generator(self.params)
                async for result in output_generator:
                    if result.get('job_state') == 'done':
                        result['result_data']['request_start_time'] = start_time
                        await self.process_job_result(result)
                    else:
                        await self.process_progress_result(result)
                    if self.error_event.is_set():
                        break
            except AttributeError:
                self.error = 'You need version >= 0.8.4 of AIME API Client Interface'
                self.error_event.set()
                self.all_jobs_done_event.set()
            except Exception as error:
                self.error_event.set()
                self.all_jobs_done_event.set()
                self.error = error
                if self.args.debug:
                    raise error
            finally:
                if self.jobs.final_job_finished or self.error_event.is_set():
                    self.all_jobs_done_event.set()


    @property
    def header_height(self):
        return len(self.header)


    @staticmethod
    def get_unit(args):
        """Getting the unit of the generated objects like 'tokens' for llms and 'images' for image generators.

        Returns:
            str: The unit string of the generated objects
        """
        if 'chat' in args.endpoint_name:
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

    @staticmethod
    def align_coloured_string(input_string, length):
        """
        Aligns a string to the specified length, considering ANSI color codes.
        
        Parameters:
            input_string (str): The string containing ANSI color codes.
            length (int): The desired length of the string.
        
        Returns:
            str: The aligned string.
        """
        visible_string = BenchmarkApiEndpoint.clean_ansi_string(input_string)
        visible_length = len(visible_string)
        
        if visible_length > length:
            truncated_string = visible_string[:length]
            final_string = input_string[:input_string.index(truncated_string[-1]) + 1]
            return final_string + RESET
        else:
            padding = ' ' * (length - visible_length)
            return input_string + padding

    @staticmethod
    def clean_ansi_string(input_string):
        ansi_escape = re.compile(r'\033(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', input_string)


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

    def __init__(self, args, header_height, lock):
        self.args = args
        self.num_generated_units = self.args.num_units
        self.title_bar_list = self.init_table_title(header_height)
        self.positions = PositionHandler(header_height, lock)
        self.current_jobs = dict()
        self.last_progress_dict = dict()
        self.current_rate_dict = dict()
        self.unit, self.unit_scale, self.unit_precision = BenchmarkApiEndpoint.get_unit(self.args)

    async def new(self, job_id, current_header_height):
        """Initializing the progress bar of the job with the given job ID.

        Args:
            job_id (str): Job ID of the related job
        """
        self.current_jobs[job_id] = tqdm(
            total=self.num_generated_units, # the unit_scale arg in tqdm shows wrong rate for sdxl
            unit=' ' + self.unit,
            position=await self.positions.new(job_id) + current_header_height + 2,
            desc=f'{job_id[:WIDTH_COLUMN_JOB_ID]:<{WIDTH_COLUMN_JOB_ID}}',
            leave=False,
            bar_format=f'{{desc}} | {{percentage:3.0f}}% {{bar}}| {{n:.{self.unit_precision}f}} / {{total:.{self.unit_precision}f}} |   {{elapsed}} < {{remaining}}  | ' '{rate_noinv_fmt} {postfix}',
            dynamic_ncols=True,
            colour='blue'
            )

    def get(self, job_id):
        return self.current_jobs.get(job_id)


    async def update(self, progress_info, current_header_height):
        """Updating the related progress bar with the given progress state.

        Args:
            progress_info (dict): Job progress information containing the job_id and the progress state like number of generated tokens so far or percentage.
        """
        job_id = progress_info.get('job_id')
        
        current_progress_bar = self.current_jobs.get(job_id)
        if current_progress_bar:
            await self.positions.update(self.current_jobs, current_header_height)
            current_progress = progress_info.get('progress')
            if current_progress is not None:
                if 'chat'in self.args.endpoint_name:
                    if self.num_generated_units < current_progress:
                        current_progress_bar.total = current_progress
                    else:
                        current_progress_bar.total = self.num_generated_units
                current_progress_bar.n = current_progress * self.unit_scale

                if self.positions.get(job_id) == 1:
                    self.update_table_title(current_progress, current_header_height)
                self.measure_current_rate(progress_info)
                current_progress_bar.refresh()


    async def remove(self, job_id):
        """Removing the progress bar of finished jobs with the given job id.

        Args:
            job_id (str): Job ID of the related job
        """
        await self.positions.release(job_id)
        current_progress_bar = self.current_jobs.get(job_id)     
        if current_progress_bar:
            current_progress_bar.close()
            self.current_jobs.pop(job_id, None)
            self.current_rate_dict.pop(job_id, None)
            self.last_progress_dict.pop(job_id, None)


    def init_table_title(self, header_height):
        return [
            tqdm(
                total=0,
                bar_format='{desc}',
                leave=False,
                position=idx,
                colour='red',
                dynamic_ncols=True
            ) for idx in range(header_height+1, header_height+3)
        ]


    def update_table_title(self, current_progress, current_header_height):
        """Setting the column descriptions and adjusting the position of the table title bar for the progress bar table.
        """
        if self.current_rate_dict:
            rate = [element for element in self.current_rate_dict.values()][0]
        else:
            rate = 0
        screen_width = self.title_bar_list[0].ncols
        column_title_job_id = 'JOB ID'
        column_title_job_id += ' ' * (WIDTH_COLUMN_JOB_ID - len(column_title_job_id))
        length_column_progress_unit = len(f'| {(current_progress * self.unit_scale):.{self.unit_precision}f} / {self.num_generated_units:.{self.unit_precision}f}')
        length_rate_column = len(f' {tqdm.format_sizeof(rate) + " " if current_progress else "?"}{self.unit}/s ')
        column_title_progress_unit = f'{f"| {self.unit}":<{length_column_progress_unit}}'
        column_title_duration = ' | Elapsed < Remain | ' if current_progress else ' | Elap. < Rem. | '
        column_title_benchmark = f'{"Benchmark":<{length_rate_column}}'
        right_bar = column_title_progress_unit + column_title_duration + column_title_benchmark
        length_progress_bar = max(screen_width - len(column_title_job_id + right_bar), 9)
        column_title_progress_percentage = f'{" | Progress in percentage"[:length_progress_bar]:<{length_progress_bar}}'
        title_str = column_title_job_id + column_title_progress_percentage + right_bar
        for idx, description in enumerate(( title_str[:screen_width], '-' * screen_width )):
            position = current_header_height + idx + 1
            if self.title_bar_list[idx].desc != description or self.title_bar_list[idx].pos != position:
                
                self.title_bar_list[idx].pos = position
                self.title_bar_list[idx].clear()
                self.title_bar_list[idx].set_description_str(description)
                self.title_bar_list[idx].refresh()


    def measure_current_rate(self, progress_info, update_interval=1):
        job_id = progress_info.get('job_id')
        current_progress = progress_info.get('progress')
        tic = time.time()
        last_progress, time_last_progress = self.last_progress_dict.get(job_id, (None, None))
        if last_progress:
            if ((tic - time_last_progress) > update_interval):
                if self.current_rate_dict.get(job_id):
                    self.current_rate_dict[job_id] = 0.9 * self.current_rate_dict[job_id] + 0.1 * ((current_progress - last_progress) * self.unit_scale / (tic - time_last_progress))
                else:
                    self.current_rate_dict[job_id] = (current_progress - last_progress) * self.unit_scale / (tic - time_last_progress) 
                self.last_progress_dict[job_id] = current_progress, tic
        else:
            self.last_progress_dict[job_id] = current_progress, tic


    def get_current_rate_total(self):
        return sum(self.current_rate_dict.values())

    def get_current_rate_single(self):
        return statistics.mean(self.current_rate_dict.values() or [0])



class PositionHandler():

    def __init__(self, header_height, lock):
        self._counter = 0
        self.header_height = header_height
        self.vacant = list()
        self.running_jobs = dict()
        self.lock = lock


    async def new(self, job_id):
        async with self.lock:
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
        current_progress_bar.pos = target_position + self.header_height + 2
        self.running_jobs[job_id] = target_position
        if current_position != target_position:
            self.vacant.remove(target_position)
            self.vacant.append(current_position)


    async def update(self, progress_bar_dict, current_header_height):
        running_jobs = self.running_jobs.copy()
        async with self.lock:
            header_changed = self.header_height != current_header_height
            self.header_height = current_header_height
            if self.vacant and min(self.vacant) < max(running_jobs.values()) or header_changed:     
                for job_id, position in sorted(running_jobs.items()):
                    if header_changed:
                        self.set_position(position, position, job_id, progress_bar_dict)
                    elif self.vacant:
                        min_vacant = min(self.vacant)
                        if position > min_vacant:
                            self.set_position(position, min_vacant, job_id, progress_bar_dict)


    async def release(self, job_id):
        async with self.lock:
            self.vacant.append(self.get(job_id))
            self.running_jobs.pop(job_id, None)


class JobHandler():

    def __init__(self, args, lock):
        self.args = args
        self.num_running = 0
        self.last_update_time = time.time()
        self.last_update_num_running = 0
        self.max_num_running = 0
        self.num_finished = 0
        self.lock = lock
        self.first_batch_jobs = dict()
        self.num_first_batch = 0
        self.finished_job_batches = list()
        self.mean_durations = dict()
        self.mean_single_rates = dict()
        self.mean_batch_rates = dict()


    @property
    def final_job_finished(self):
        return self.num_finished == self.args.total_requests + self.num_first_batch


    async def update(self, progress_bar_dict):
        async with self.lock:
            self.num_running = sum([1 for progress_bar in progress_bar_dict.values() if 0 < progress_bar.n])
            if (time.time() - self.last_update_time) > 1:
                self.last_update_time = time.time()
                if self.last_update_num_running == self.num_running and self.num_running > self.max_num_running:
                    self.max_num_running = self.num_running
                self.last_update_num_running = self.num_running


    def collect_first_batch_jobs(self, progress_bar_dict):
        if self.num_first_batch < self.num_running:
            self.first_batch_jobs = {job_id: progress_bar for job_id, progress_bar in progress_bar_dict.items() if progress_bar.n}
            self.num_first_batch = self.num_running


    async def finish(self, result, finish_time):

        job_stats = dict()
        num_generated_units = result.get('num_generated_tokens', self.args.num_units)
        num_input_units = result.get('prompt_length', 1)
        durations = {
            'total_job': finish_time - result.get('request_start_time', 0),
            'worker_pending': result.get('pending_duration') or 0,
            'worker_preprocessing': result.get('preprocessing_duration') or 0,
            'worker_compute': result.get('finished_time', 0) - result.get('arrival_time', 0),
            'transfer_client2server': result.get('start_time', 0) - result.get('request_start_time', 0),
            'transfer_server2worker': result.get('arrival_time', 0) - result.get('start_time_compute', 0),
            'transfer_worker2server': result.get('result_sent_time', 0) - result.get('finished_time', 0),
            'transfer_server2client': finish_time - result.get('result_received_time', 0)
        }
        durations['worker_generation'] = durations['worker_compute'] - durations['worker_pending'] - durations['worker_preprocessing']
        durations['total_from_server'] = result.get('total_duration', 0)
        durations['compute_from_server'] = result.get('compute_duration', 0)
        durations['server_pending'] = result.get('start_time_compute', 0) - result.get('start_time', 0)
        job_stats['durations'] = durations
        job_stats['rates'] = {
            key: self.get_rate(
                num_input_units if key in ('worker_preprocessing', 'transfer_client2server', 'transfer_server2worker')  else num_generated_units,
                job_stats['durations'][key]
            ) for key in RATE_TYPES
        }
        async with self.lock:
            self.num_finished += 1
            if not self.finished_job_batches or (len(self.finished_job_batches[-1]) == self.args.concurrent_requests) or self.args.serial_processing_worker:
                self.finished_job_batches.append(list())

            self.finished_job_batches[-1].append(job_stats)
            self.mean_durations = self.get_mean('durations') or dict()
            self.mean_single_rates = self.get_mean('rates') or dict()
            self.mean_batch_rates = self.get_mean_batch_rates()

            if not self.args.no_warmup and len(self.finished_job_batches[-1]) == self.num_first_batch:
                self.finished_job_batches.clear()



    def get_rate(self, num_units, duration):
        return num_units / duration if duration else None


    def get_mean_batch_rates(self):
        all_batch_rates = {key: list() for key in RATE_TYPES}

        for job_batch in self.finished_job_batches:
            if len(job_batch) >= self.args.concurrent_requests or self.args.serial_processing_worker:
                batch_rates = self.get_batch_rates(job_batch)
                for key, value in batch_rates.items():
                    all_batch_rates[key].append(value)
        return {key: statistics.mean(rate) for key, rate in all_batch_rates.items() if rate}


    def get_batch_rates(self, job_batch):
        batch_rates = dict()
        for key in RATE_TYPES:
            values = [job['rates'].get(key) for job in job_batch if job['rates'].get(key)]
            if values:
                batch_rates[key] = sum(values)
        return batch_rates


    def get_mean(self, value_type):
        scores_all = [job.get(value_type) for job_batch in self.finished_job_batches for job in job_batch]
        if scores_all:     
            mean_dict = dict()
            for key in next(iter(scores_all)).keys():
                score_values = [scores.get(key) for scores in scores_all if scores.get(key) is not None]
                mean_dict[key] = statistics.mean(score_values) if score_values else None
            return mean_dict


def main():
    benchmark_api = BenchmarkApiEndpoint()
    try:
        benchmark_api.run()
    finally:
        
        for title_bar in benchmark_api.progress_bars.title_bar_list:
            title_bar.clear()
        for header_line in benchmark_api.header:
            header_line.clear()
        for progress_bar in benchmark_api.progress_bars.current_jobs.values():
            progress_bar.clear()
        benchmark_api.show_cursor()


if __name__ == "__main__":
	main()

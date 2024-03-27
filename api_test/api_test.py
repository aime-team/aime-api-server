# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

import requests
import subprocess
import asyncio
import argparse
import time
import pytest
import psutil
import json
import toml
import aiohttp
from aime_api_client_interface import ModelAPI, do_api_request, do_api_request_async
import atexit
from PIL import Image, UnidentifiedImageError
import numpy as np
import io
import base64
import binascii

import tracemalloc


tracemalloc.start()
EP_CONFIG_FILE_MAIN_TESTWORKER = 'api_test/endpoints/api_test_endpoint.cfg'
EP_CONFIG_FILE_CROP_TESTWORKER = 'api_test/endpoints/api_test_endpoint_crop.cfg'
EP_CONFIG_FILES = EP_CONFIG_FILE_MAIN_TESTWORKER + ',' + EP_CONFIG_FILE_CROP_TESTWORKER
HOST = '0.0.0.0'
PORT = '7777'
TYPES_DICT = {'string': str, 'integer':int, 'float':float, 'image': bytes}
CLIENT_LOGIN_KEY = '6a17e2a5b70603cb1a3294b4a1df67da'




def load_flags():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-H', '--host', type=str, default="0.0.0.0", required=False, help='Host address [default 0.0.0.0]'
                        )
    parser.add_argument(
        '-p', '--port', type=int, default='7777', required=False, help='Port number'
                        )
    parser.add_argument(
        '-wp', '--worker_processes', type=int, default=1, required=False, help='Number of api server worker processes [default 1]'
                        )
    parser.add_argument(
        '--dev', '--debug', action='store_true', required=False, help='Run the server in debug/development mode'
                        )
    parser.add_argument(
        '--hide_logging', action='store_true', required=False,
        help='Hide API Server logging in console'
                        )
    parser.add_argument(
        '-tr', '--total_requests', type=int, default=100, required=False, help='Number of api server worker processes [default 1]'
                        )
    
    return parser.parse_known_args()

class ApiTest():
    def __init__(self, args, ep_config_files, number_of_main_test_workers):
        self.args = args
        self.number_of_main_test_workers = number_of_main_test_workers
        self.ep_config_files = ep_config_files
        self.ep_config_dict, self.endpoint_names = self.get_ep_config_dict()
        self.proc_api_server = self.init_api_server()
        time.sleep(2)
        self.client_session_auth_key_dict = self.get_client_session_auth_key_dict()
        self.proc_main_test_workers = self.init_multiple_main_test_workers()
        
        self.proc_crop_test_worker = self.init_api_test_worker(self.ep_config_dict.get(self.endpoint_names[1]).get('WORKER').get('job_type')) if len(self.endpoint_names) > 1 else None
        self.dicts_with_required_parameters_for_all_endpoints = self.get_dict_with_required_parameters_for_all_endpoints()
                

    def run_performance_tests(self):
            self.make_multiple_requests_on_main_endpoint()
            self.make_multiple_async_requests_on_main_endpoint()


    def init_api_server(self):
        command = [
            'python3',
            'run_api_server.py',
            '--host', self.args.host,
            '--port', str(self.args.port),
            '--ep_config', self.ep_config_files,
            '--worker_processes',
            str(self.args.worker_processes),
            '--dev',
            '--hide_logging',
            '--no_sanic_logger'
        ]

        return subprocess.Popen(command, stdout=subprocess.PIPE)


    def get_client_session_auth_key_dict(self):
        client_session_auth_key_dict = {}
        for endpoint_name in self.ep_config_dict:
            try:
                url = f'http://{self.args.host}:{self.args.port}/{endpoint_name}/login'
                params = {'user': 'aime', 'key': CLIENT_LOGIN_KEY}
                response = requests.get(url=url, params=params)
                client_session_auth_key_dict[endpoint_name] = response.json().get('client_session_auth_key')
            except requests.exceptions.ConnectionError:
                pytest.fail(f'Getting client session auth key failed. API server: http://{self.args.host}:{self.args.port} not available')
                        
        return client_session_auth_key_dict


    def init_api_test_worker(self, worker_job_type):
        return subprocess.Popen(['python3', 'api_test/api_test_worker.py','--api_server', f'http://{self.args.host}:{self.args.port}', '--worker_job_type', worker_job_type])


    def init_multiple_main_test_workers(self):
        return [self.init_api_test_worker(self.ep_config_dict.get('api_test').get('WORKER').get('job_type')) for _ in range(self.number_of_main_test_workers)]


    def init_main_test_worker_with_invalid_worker_auth_key(self):
        proc = subprocess.Popen(
            [
                'python3',
                'api_test/api_test_worker.py',
                '--api_server',
                f'http://{self.args.host}:{self.args.port}',
                '--worker_job_type',
                self.ep_config_dict.get('api_test').get('WORKER').get('job_type'),
                '--worker_auth_key', 'This_is_an_invalid_auth_key'
            ], 
            stderr=subprocess.PIPE, 
            stdout=subprocess.PIPE
        )
        stdout, stderr = proc.communicate()
        exit_code = proc.wait()
        assert exit_code == 1, f'WARNING: Test with unauthorized worker did not respond with exitcode 1'
        assert b'! API server responded with error: Worker not authorized' in stderr, f'WARNING: Test with unauthorized worker responded with exitcode 1 but got the message "{stderr.decode()}"'       
        return True, stderr.decode()


    def init_main_test_worker_with_invalid_job_type(self):
        proc = subprocess.Popen(
            [
                'python3',
                'api_test/api_test_worker.py',
                '--api_server',
                f'http://{self.args.host}:{self.args.port}',
                '--worker_job_type',
                'This_is_an_invalid_job_type'
            ],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        stdout, stderr = proc.communicate()
        exit_code = proc.wait()
        assert exit_code == 1, f'WARNING: Test with unauthorized job type did not respond with exitcode 1'
        assert b'! API server responded with error: No job queue for job_type' in stderr, f'WARNING: Test with unauthorized job type responded with exitcode 1 but got the message "{stderr.decode()}"'
        return True, stderr.decode()


    def make_single_async_test_request_on_main_endpoint(self):
        #loop = self.get_loop()
        return asyncio.run(self.make_async_request_on_main_endpoint(self.dicts_with_required_parameters_for_all_endpoints.get(self.endpoint_names[0])))


    def make_multiple_requests_on_main_endpoint(self):
        print(f'Making {self.args.total_requests} synchronous requests on {self.number_of_main_test_workers} instances of {self.endpoint_names[0]}...', end='', flush=True)

        #loop = self.get_loop()
        start = time.time()
        start_total = start
        for _ in range(self.args.total_requests):
            self.make_sync_request_on_main_endpoint(self.dicts_with_required_parameters_for_all_endpoints.get(self.endpoint_names[0]))
        self.print_performance_results(time.time() - start)
        

    def make_multiple_async_requests_on_main_endpoint(self):
        print(f'Making {self.args.total_requests} asynchronous requests on {self.number_of_main_test_workers} instances of {self.endpoint_names[0]}...', end='', flush=True)
        loop = self.get_loop()
        start = time.time()
        tasks = [asyncio.ensure_future(self.make_async_request_on_main_endpoint(self.dicts_with_required_parameters_for_all_endpoints.get(self.endpoint_names[0])), loop=loop) for _ in range(self.args.total_requests)]
        loop.run_until_complete(asyncio.gather(*tasks))
        self.print_performance_results(time.time() - start)


    def make_client_request_with_base64_image(self, image, endpoint_name):

        params = dict(self.dicts_with_required_parameters_for_all_endpoints.get(endpoint_name), **{'image': image})
        try:
            response = self.fetch_sync(params, endpoint_name)
            assert response.status_code == 200, f'{response.text}'
            return response

        except requests.exceptions.ConnectionError as exc:
            pytest.fail(f'No connection to server http://{self.args.host}:{self.args.port} possible')
            return False


    def make_request_with_invalid_client_session_auth_key_on_main_endpoint(self):
        params = self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint('client_session_auth_key', 'this_is_an_invalid_key')
        try:
            response = self.fetch_sync(params, self.endpoint_names[0])
            assert response.status_code == 401, f'Invalid client_session authentification key "{params["client_session_auth_key"]}" did not reply with status code 401'
            return True , response.json().get('errors')


        except requests.exceptions.ConnectionError as exc:
            pytest.fail(f'No connection to server http://{self.args.host}:{self.args.port} possible')
            return False

    
    def make_request_with_invalid_parameters(self, params):
        try:    
            response = self.fetch_sync(params, self.endpoint_names[0])
            assert response.status_code == 400, f'Invalid parameters {params} did not reply with status code 400'
            return True


        except requests.exceptions.ConnectionError as exc:
            pytest.fail(f'No connection to server http://{self.args.host}:{self.args.port} possible')
            return False


    def check_image_resizing_for_given_client_output_test_image_on_given_endpoint(self, endpoint_name, client_output_test_image):
        ep_config = self.ep_config_dict.get(endpoint_name)
        ep_inputs = ep_config.get('INPUTS')
        min_size = tuple(ep_inputs.get('image').get('size').get('minimum'))
        max_size = tuple(ep_inputs.get('image').get('size').get('maximum'))
        align_values = tuple(ep_inputs.get('image').get('size').get('align'))
        option_resize_method = ep_inputs.get('image').get('size').get('resize_method')
        
        worker_input_test_image_expected_format = ep_inputs.get('image').get('format').get('default')
        worker_input_test_image_expected_color_space = ep_inputs.get('image').get('color_space').get('default')
        client_output_test_image_64 = convert_image_to_base64_string(client_output_test_image, client_output_test_image.format)
        response = self.make_client_request_with_base64_image(client_output_test_image_64, endpoint_name)

        def shorten_strings(obj, max_length=10):
            if isinstance(obj, dict):
                return {key: shorten_strings(value, max_length) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [shorten_strings(item, max_length) for item in obj]
            elif isinstance(obj, str) and len(obj) > max_length:
                return obj[:max_length] + "..."
            elif isinstance(obj, bytes) and len(obj) > max_length:
                return obj[:max_length] + b"..."
            else:
                return obj

        #print('response', shorten_strings(response.json(), 30))
        worker_input_test_image = convert_base64_str_list_to_image_list(response.json().get('images'))[0]
        assert min_size <= worker_input_test_image.size <= max_size, f'Resizing failed: min: {min_size}, max: {max_size}, converted size: {worker_input_test_image.size}'
        for image_size_value, align_value in zip(worker_input_test_image.size, align_values):
            assert image_size_value % align_value == 0
            
        assert worker_input_test_image.format.lower() == worker_input_test_image_expected_format.lower(), f'{worker_input_test_image.format} != {worker_input_test_image_expected_format}'
        assert worker_input_test_image.mode.lower() == worker_input_test_image_expected_color_space.lower(), f'{worker_input_test_image.mode} != {worker_input_test_image_expected_color_space}'
        report = f'Client output image got resized from {client_output_test_image.size[0]}x{client_output_test_image.size[1]} to {worker_input_test_image.size[0]}x{worker_input_test_image.size[1]} in {endpoint_name} with the method "{option_resize_method}".\n' \
        f'The original image had the format {client_output_test_image.format} and was converted to {worker_input_test_image.format}'
        return report


    def check_image_resizing_on_given_endpoint(self, endpoint_name):
        reports = []
        client_output_test_image_binary = get_test_image()
        with io.BytesIO(client_output_test_image_binary) as buffer:
            client_output_test_image = Image.open(buffer)
            ep_inputs = self.ep_config_dict.get(endpoint_name).get('INPUTS')
            min_size = ep_inputs.get('image').get('size').get('minimum')
            max_size = ep_inputs.get('image').get('size').get('maximum')

            client_output_test_image_too_small = resize_test_image(client_output_test_image, min_size[0]-1, min_size[1]-1)
            #client_output_test_image_too_big = resize_test_image(client_output_test_image, max_size[0]+1, max_size[1]+1)
        reports.append(self.check_image_resizing_for_given_client_output_test_image_on_given_endpoint(endpoint_name, client_output_test_image_too_small))
        #reports.append(self.check_image_resizing_for_given_client_output_test_image_on_given_endpoint(endpoint_name, client_output_test_image_too_big))
        return reports


    def check_image_resizing(self):
        reports = []
        for endpoint_name in self.endpoint_names:
            reports += self.check_image_resizing_on_given_endpoint(endpoint_name)
        return True, reports


    async def make_async_request_on_main_endpoint(self, params):
        try:
            response_json = await self.fetch_async_on_main_endpoint(params)
            assert response_json['text'] == 'Test output', 'Test output not matching'
            return True

        except aiohttp.ClientError as exc:
            pytest.fail(f'Error making request to http://{self.args.host}:{self.args.port}/{self.endpoint_names[0]}: {exc}')
            return False
    

    def make_sync_request_on_main_endpoint(self, params):
        try:
            response = self.fetch_sync(params, self.endpoint_names[0])
            assert response.status_code == 200, response.status_code
            assert response.json()["text"] == 'Test output'

        except requests.exceptions.ConnectionError as exc:
            pytest.fail(f'No connection to server http://{self.args.host}:{self.args.port} possible')


    async def fetch_async_on_main_endpoint(self, params):
        async with aiohttp.ClientSession() as session:
            async with session.post(f'http://{self.args.host}:{self.args.port}/' + self.endpoint_names[0], json=params) as response:
                assert response.status == 200, await response.json()
                return await response.json()


    def fetch_sync(self, params, endpoint_name):
        return requests.post(f'http://{self.args.host}:{self.args.port}/' + endpoint_name, json=params)


    def print_performance_results(self, duration):
        print(f'Done. Time needed: {round(duration, 1)} seconds -> {round(self.args.total_requests/duration, 1)} requests/sec')


    def exit_processes(self):

        self.kill_processes_with_children(self.proc_api_server)
        for proc in self.proc_main_test_workers:
            self.kill_processes_with_children(proc)
        if self.proc_crop_test_worker:
            self.kill_processes_with_children(self.proc_crop_test_worker)
        

    def kill_processes_with_children(self, proc):
        for child in psutil.Process(proc.pid).children(recursive=True):
            if child.is_running():
                child.kill()
        proc.kill()
        proc.wait()


    def get_loop(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop


    def get_dict_with_required_parameters_and_ep_input_on_main_endpoint(self, ep_input, value):
        return dict(self.dicts_with_required_parameters_for_all_endpoints.get(self.endpoint_names[0]), **{ep_input: value})


    def get_invalid_parameters_from_main_endpoint_config(self):
        invalid_parameters = []
        
        invalid_parameters.append(self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint('unknown_parameter', 'value'))
        ep_inputs = self.ep_config_dict.get('api_test').get('INPUTS')
        for ep_input in ep_inputs:
            arg_definition = ep_inputs[ep_input]
            if not arg_definition.get('required', False):
                arg_type = TYPES_DICT[arg_definition.get('type', 'string')]
                if arg_type in (int, float):
                    invalid_parameters.append(self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint(ep_input, arg_definition.get('minimum', 0) -1))
                    invalid_parameters.append(self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint(ep_input, arg_definition.get('maximum', 0) +1))
                if arg_type is int:
                    invalid_parameters.append(self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint(ep_input, 'a'))
                if arg_type is float:
                    invalid_parameters.append(self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint(ep_input, '1.0'))
                if arg_type is str:
                    invalid_parameters.append(self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint(ep_input, 1.1))
                    invalid_parameters.append(self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint(ep_input, 1))
                    if arg_definition.get('max_length', None):
                        invalid_parameters.append(self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint(ep_input, '_'*(arg_definition.get('max_length')+1)))

        return invalid_parameters


    def create_dict_with_required_parameters(self, endpoint_name):
        ep_inputs = self.ep_config_dict.get(endpoint_name).get('INPUTS')
        required_parameters_name_list = [ep_input for ep_input in ep_inputs if ep_inputs[ep_input].get('required', False)]
        dict_with_required_parameters = {}
        arg_type = TYPES_DICT[ep_inputs.get('type', 'string')]
        for required_parameter_name in required_parameters_name_list:
            required_parameter = ep_inputs[required_parameter_name]
            if required_parameter_name == 'client_session_auth_key':
                dict_with_required_parameters[required_parameter_name] = self.client_session_auth_key_dict.get(endpoint_name)
            elif required_parameter.get('default', None):
                dict_with_required_parameters[required_parameter_name] = ep_inputs[required_parameter].get('default')
            elif required_parameter.get('max_length', None):
                dict_with_required_parameters[required_parameter_name] = '_'*required_parameter.get('max_length')
            elif required_parameter.get('maximum', None):
                dict_with_required_parameters[required_parameter_name] = required_parameter.get('maximum')
            elif required_parameter.get('minimum', None):
                dict_with_required_parameters[required_parameter_name] = required_parameter.get('minimum')
            else:
                dict_with_required_parameters[required_parameter_name] = ApiTest.make_example_value(arg_type)

        return dict_with_required_parameters


    def get_dict_with_required_parameters_for_all_endpoints(self):
        dicts_with_required_parameters_for_all_endpoints = {}
        for endpoint_name in self.endpoint_names:
            dicts_with_required_parameters_for_all_endpoints[endpoint_name] = self.create_dict_with_required_parameters(endpoint_name)
        return dicts_with_required_parameters_for_all_endpoints


    @staticmethod
    def make_example_value(arg_type):
        if arg_type is str:
            return "example_string"
        elif arg_type is int:
            return 42
        elif arg_type is float:
            return 23.7


    @staticmethod
    def get_ep_config(ep_config_file):
        ep_configs = {}
        with open(ep_config_file, "r") as f:
            ep_config = toml.load(f)
        return ep_config


    def get_ep_config_dict(self):
        ep_config_dict = {}
        endpoint_names = []
        for ep_config_file in self.ep_config_files.split(','):
            ep_config = ApiTest.get_ep_config(ep_config_file)
            endpoint_name = ep_config.get('ENDPOINT').get('name')
            ep_config_dict[endpoint_name] = ep_config
            endpoint_names.append(endpoint_name)
        return ep_config_dict, endpoint_names

    
    def run_model_api_test(self):
        test_image = get_test_image()

        params = self.get_dict_with_required_parameters_and_ep_input_on_main_endpoint('image', test_image)
    
        #params['format'] = self.ep_config_dict.get(self.endpoint_names[0]).get('INPUTS').get('image').get('format').get('default')
        callback = Callback()
        callback_async = CallbackAsync()
        
        
        result = asyncio.run(do_api_request_async(f'http://{self.args.host}:{self.args.port}', self.endpoint_names[0], params, 'aime', CLIENT_LOGIN_KEY, callback.result_callback, callback.progress_callback))
        success = validate_result_image(result)
        assert success, f'Test for async request on model_api simple interface with sync callbacks on main test worker with the endpoint {api_test.endpoint_names[0]}  failed\nResults: {result}'

        result = asyncio.run(do_api_request_async(f'http://{self.args.host}:{self.args.port}', self.endpoint_names[0], params, 'aime', CLIENT_LOGIN_KEY, callback_async.result_callback, callback_async.progress_callback))
        success = validate_result_image(result)
        assert success, f'Test for async request on model_api simple interface with async callbacks on main test worker with the endpoint {api_test.endpoint_names[0]}  failed\nResults: {result}'

        result = do_api_request(f'http://{self.args.host}:{self.args.port}', self.endpoint_names[0], params, 'aime', CLIENT_LOGIN_KEY, callback.progress_callback)
        success = validate_result_image(result)
        assert success, f'Test for sync request on model_api simple interface with progress callback on main test worker with the endpoint {api_test.endpoint_names[0]}  failed\nResults: {result}'

        model_api = ModelAPI(f'http://{self.args.host}:{self.args.port}', self.endpoint_names[0], 'aime', CLIENT_LOGIN_KEY)
        model_api.do_api_login()
        result = model_api.do_api_request(params, callback.progress_callback)
        success = validate_result_image(result)
        assert success, f'Test for sync request on model_api with progress callback on main test worker with the endpoint {api_test.endpoint_names[0]}  failed\nResults: {result}'

        result = asyncio.run(self.run_async_model_api_test(params, callback))
        success = validate_result_image(result)
        assert success, f'Test for async request on model_api with sync callbacks on main test worker with the endpoint {api_test.endpoint_names[0]}  failed\nResults: {result}'

        result = asyncio.run(self.run_async_model_api_test(params, callback_async))
        success = validate_result_image(result)
        assert success, f'Test for async request on model_api with sync callbacks on main test worker with the endpoint {api_test.endpoint_names[0]}  failed\nResults: {result}'
        
        model_api_no_login = ModelAPI(f'http://{self.args.host}:{self.args.port}', self.endpoint_names[0], 'aime', CLIENT_LOGIN_KEY)
        with pytest.raises(ConnectionRefusedError) as excinfo:  
            _ = model_api_no_login.do_api_request(params, callback.progress_callback, callback.progress_error_callback)
            assert excinfo
        
        with pytest.raises(ConnectionRefusedError) as excinfo:  
            _ = asyncio.run(self.run_async_model_api_test_no_login(params, callback_async))
            assert excinfo

        result_no_prgress = do_api_request(f'http://{self.args.host}:{self.args.port}', self.endpoint_names[0], params, 'aime', CLIENT_LOGIN_KEY)
        success = validate_result_image(result)
        
        
        model_api_invalid_url = ModelAPI(f'http://wrong_url', self.endpoint_names[0])

        with pytest.raises(ConnectionError) as excinfo:  
            model_api_invalid_url.do_api_login()
            assert excinfo

        with pytest.raises(ConnectionError) as excinfo:  
            asyncio.run(self.run_async_model_invalid_url_test())
            assert excinfo
        
        return True

    async def run_async_model_invalid_url_test(self):
        model_api_invalid_url = ModelAPI(f'http://wrong_url', self.endpoint_names[0], 'aime', CLIENT_LOGIN_KEY)
        await model_api_invalid_url.do_api_login_async()
        await model_api.close_session()

    async def run_async_model_api_test(self, params, callback):
        model_api = ModelAPI(f'http://{self.args.host}:{self.args.port}', self.endpoint_names[0], 'aime', CLIENT_LOGIN_KEY)
        _ = await model_api.do_api_login_async(None)
        result = await model_api.do_api_request_async(params, callback.result_callback, callback.progress_callback)
        await model_api.close_session()
        return result

    async def run_async_model_api_test_no_login(self, params, callback):
        model_api = ModelAPI(f'http://{self.args.host}:{self.args.port}', self.endpoint_names[0], 'aime', CLIENT_LOGIN_KEY)
        result = await model_api.do_api_request_async(params, callback.result_callback, callback.progress_callback)
        await model_api.close_session()
        return result


def validate_result_image(result, progress_info=None):
    assert result, f'No result.\nResult: {result}\nProgress info: {progress_info}'

    result_str = ''
    for key, value in result.items():
        result_str += f'{key}: '
        result_str += f'{value[:40]}\n' if type(value) == str else f'{value}\n'
    if not progress_info or progress_info.get('queue_position') != -1:
        assert 'images' in result, f'Job result: {result_str}\nKey "images" missing client job result'
        binary_images = result.get('images')
        #print('image: ', binary_images)
        assert binary_images, f'Job result: {result_str}\nParameter "images" in client job result is None'
        #assert isinstance(binary_images, bytes) or all([isinstance(binary_image, bytes) for binary_image in binary_images])
    return True

class CallbackAsync():
    def __init__(self):
        self.current_progress = 0


    async def result_callback(self, result):

        validate_result_image(result)

        assert result['success'], f'Test of python client interface do_api_request not successful.\n Response: {result_str}'


    async def progress_callback(self, progress_info, progress_data):
        if progress_data:
            validate_result_image(progress_data, progress_info)
    


    


class Callback():


    def __init__(self):
        self.current_progress = 0


    def result_callback(self, result):

        validate_result_image(result)

        assert result['success'], f'Test of python client interface do_api_request not successful.\n Response: {result_str}'


    def progress_callback(self, progress_info, progress_data):
        if progress_data:
            validate_result_image(progress_data, progress_info)
    
    def progress_error_callback(self, response):
        pass
        print(response)

def main():
    args, _ = load_flags()

    api_test = ApiTest(args, EP_CONFIG_FILES, 1)
    invalid_parameters = api_test.get_invalid_parameters_from_main_endpoint_config()

    if api_test.make_single_async_test_request_on_main_endpoint():
        print(f'Test for single async request on test worker with the endpoint {api_test.endpoint_names[0]}  successful')
    if all(api_test.make_request_with_invalid_parameters(parameters) for parameters in invalid_parameters):
        print('Test requests with invalid parameters return statuscode "400" as supposed')
    success = api_test.run_model_api_test()
    if success:
        print(f'Test with python interface model_api.py successful')  
    success, message = api_test.init_main_test_worker_with_invalid_worker_auth_key()
    if success:
        print(f'Test with unauthorized worker key responded with exitcode 1 and the message "{message.strip()}" as supposed')
    success, message = api_test.init_main_test_worker_with_invalid_job_type()
    if success:
        print(f'Test with unauthorized worker job type responded with exitcode 1 and the message "{message.strip()}" as supposed')
    success, message = api_test.make_request_with_invalid_client_session_auth_key_on_main_endpoint()
    if success:
        print(f'Test with invalid client session authentification key responded statuscode 400 and the message "{message}" as supposed')
    success, message = api_test.check_image_resizing()
    if success:
        for single_message in message:
            print(single_message)
    
    api_test.exit_processes()
    time.sleep(2)
    print()


def report(report_string):
    print(report_string)


def get_test_image():
    with open('api_test/test_image.png', 'rb') as data:
        image_binary = data.read()
    return image_binary

def resize_test_image(image, width, height):
    resized_image = image.resize((width, height), resample=Image.Resampling.LANCZOS)
    resized_image.format = image.format
    return resized_image


def convert_image_to_base64_string(image, image_format):
    
    with io.BytesIO() as buffer:
        image.save(buffer, format=image_format)
        image_64 = f'data:image/{image_format};base64,' + base64.b64encode(buffer.getvalue()).decode('utf-8')
    return image_64


def convert_image_list_to_base64_string(self, list_images, image_format):
    """Converts given list of PIL images to base64 string with given image_format and image metadata parsed from current_job_data.

    Args:
        list_images (list [PIL.PngImagePlugin.PngImageFile, ..]): List of python pillow images to be converted
        image_format (str): Image format. f.i. 'PNG', 'JPG'

    Returns:
        str: base64 string of images
    """        
    image_64 = ''.join(convert_image_to_base64_string(image, image_format) for image in list_images)
    return image_64


def convert_base64_str_list_to_image_list(base64_list):
    return [convert_base64_string_to_image(base64_string) for base64_string in base64_list]



def convert_base64_string_to_image(base64_string):
    base64_data = base64_string.split(',')[1]
    image_data = base64.b64decode(base64_data)

    with io.BytesIO(image_data) as buffer:
        image = Image.open(buffer)
    return image


@pytest.fixture(scope='module')
def api_test_instance():
    args, _ = load_flags()
    api_test = ApiTest(args, EP_CONFIG_FILES, 1)
    
    yield api_test
    api_test.exit_processes()
    atexit.register(report, report_string='Summary:')


def test_make_single_request(api_test_instance):
    
    success =  api_test_instance.make_single_async_test_request_on_main_endpoint()
    assert success
    if success:
        report_string = f'Test for single async request on test worker with the endpoint {api_test_instance.endpoint_names[0]} successful.'
        
        atexit.register(report, report_string=report_string)

def test_make_request_with_invalid_parameters(api_test_instance):
    invalid_parameters = api_test_instance.get_invalid_parameters_from_main_endpoint_config()
    print('Following invalid parameters were tried: ')
    for parameter in invalid_parameters:
        print(parameter)
    success = all(api_test_instance.make_request_with_invalid_parameters(parameters) for parameters in invalid_parameters)
    assert success
    if success:
        report_string = f'Test requests with invalid parameters return statuscode "400" as supposed.'
        atexit.register(report, report_string=report_string)


def test_do_api_request(api_test_instance):

    args, _ = load_flags()
    success = api_test_instance.run_model_api_test()

    if success:
        print(f'Test for on api_client_interface.python.model_api on main test worker with the endpoint {api_test_instance.endpoint_names[0]} successful')
        report_string = f'Test for on api_client_interface.python.model_api on main test worker with the endpoint {api_test_instance.endpoint_names[0]} successful'
        atexit.register(report, report_string=report_string)


def test_invalid_worker_key(api_test_instance):
    success, message = api_test_instance.init_main_test_worker_with_invalid_worker_auth_key()
    assert success
    if success:
        report_string = f'Test with unauthorized worker auth key responded with exitcode 1 and the message "{message.strip()}" as supposed'
        print(report_string)
        atexit.register(report, report_string=report_string)

def test_invalid_job_type(api_test_instance):
    success, message = api_test_instance.init_main_test_worker_with_invalid_job_type()
    assert success
    if success:
        report_string = f'Test with unauthorized worker job type responded with exitcode 1 and the message "{message.strip()}" as supposed'
        print(report_string)
        atexit.register(report, report_string=report_string)
        
def test_invalid_client_session_auth_key(api_test_instance):
    success, message = api_test_instance.make_request_with_invalid_client_session_auth_key_on_main_endpoint()
    if success:
        report_string = f'Test with invalid client session authentification key responded statuscode 400 and the message "{message}" as supposed'
        print(report_string)
        atexit.register(report, report_string=report_string)

def test_resizing(api_test_instance):
    success, message = api_test_instance.check_image_resizing()
    if success:
        report_string = '\n'.join(message)
        print(report_string)
        atexit.register(report, report_string=report_string)
        



from sanic.log import logging
from sanic.response import json as sanic_json

import urllib.request # Frage an Toine: Benötigt?

import sys
import asyncio
import io
import time
from pathlib import Path

import base64

import subprocess

from PIL import Image, UnidentifiedImageError
import pickle
from mimetypes import guess_extension, guess_type


from .job_queue import JobState
from .utils import StaticRouteHandler, shorten_strings, generate_auth_key


TYPES_DICT = {'string': str, 'integer':int, 'float':float, 'bool':bool, 'image':str, 'audio':str}


class APIEndpoint():
    """AIME ML API endpoint

    Args:
        app (APIServer): Instance of APIServer()
        title (str): Endpoint title
        name (str): Endpoint name
        description (str): Endpoint description
        client_request_limit (int): Request limit per client
        provide_worker_meta_data (bool): Whether to send data like worker name to the client
        http_methods (str): Allowed http methods on this endpoint
        ep_input_param_config (dict): Input parameter configuration from endpoint config file
        ep_output_param_config (dict): Output parameter configuration from endpoint config file
        ep_progress_param_config (dict): Progress parameter configuration from endpoint config file
        ep_session_param_config (dict): Session parameter configuration from endpoint config file
        job_type (str): Job type
        worker_auth_key (str): Allowed worker authentication key
        static_files (dict): Static routes
              
    """    
    logger = logging.getLogger('API')
    def __init__(
        self,
        app,
        title,
        name,
        description,
        client_request_limit,
        provide_worker_meta_data,
        http_methods,
        version,
        ep_input_param_config,
        ep_output_param_config,
        ep_progress_param_config,
        ep_session_param_config,
        job_type, worker_auth_key,
        static_files,
        ep_config_file_path
        ):
        self.title = title
        self.endpoint_name = name
        self.description = description
        self.client_request_limit = client_request_limit
        self.provide_worker_meta_data = provide_worker_meta_data
        self.version = version
        self.ep_input_param_config = ep_input_param_config
        self.ep_input_param_config['client_session_auth_key'] = { 'type': 'string'}     # add implicit input 
        self.ep_input_param_config['wait_for_result'] = { 'type': 'bool'}     # add implicit input 
        self.ep_output_param_config = ep_output_param_config
        self.ep_progress_param_config = ep_progress_param_config
        self.ep_session_param_config = ep_session_param_config
        self.ep_config_file_path = ep_config_file_path
        self.worker_job_type = job_type
        self.worker_auth_key = worker_auth_key
        self.registered_client_session_auth_keys = dict()

        app.add_route(self.api_request, "/" + self.endpoint_name, methods=http_methods, name=self.endpoint_name)
        app.add_route(self.api_progress, "/" + self.endpoint_name + "/progress", methods=http_methods, name=self.endpoint_name + "$progress")
        app.add_route(self.get_client_session_auth_key, "/" + self.endpoint_name + "/get_client_session_auth_key", methods=http_methods, name=self.endpoint_name + "$get_client_session_auth_key")
        self.app = app
        self.add_server_static_routes(static_files)


    def add_server_static_routes(self, static_files):
        static_route_handler = StaticRouteHandler(Path(self.ep_config_file_path).parent, self.app, self.endpoint_name)
        static_route_handler.setup_static_routes(static_files)


    async def api_request(self, request):
        """Client request on route /self.endpoint_name with input parameters for the workers related to the job type 
        given in the input parameters. The client input parameters are validated and prepared for the worker job data. 
        Next an asyncio.Future() for the job is initialized where the result will be put by APIServer.worker_job_result_json() when the job is finished. 
        The job data is put to the job type related asyncio.Queue() to be accessed by the workers in APIServer().worker_job_request().
        If 'wait_for_result' is True the end result of the job is awaited via finalize_request and returned to the client. If False, 
        the client gets a quick confirmation response and the result can be requested on route 
        /self.endpoint_name/progress in the parameter 'job_result'.

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        start_time = time.time()   
        input_args = request.json if request.method == "POST" else request.args
        validation_errors = self.validate_client(input_args)

        # fast exit if not authorized for request
        if validation_errors:
            return self.handle_validation_errors(validation_errors)

        job_data, validation_errors = self.validate_input_parameters_for_job_data(input_args, start_time)
        if validation_errors:
            return self.handle_validation_errors(validation_errors)

        job_data = self.add_session_variables_to_job_data(request, job_data)
        job_data = self.prepare_job_data(job_data, start_time)
        job_future = await self.init_future_and_put_job_in_worker_queue(job_data)

        if input_args.get('wait_for_result', True):
            response = await self.finalize_request(request, job_data.get('job_id'), job_future) 
        else:
            response = {'success': True, 'job_id': job_data.get('job_id'), 'ep_version': self.version}
        return sanic_json(response)


    async def api_progress(self, request):
        """Client request on route /self.endpoint_name/progress called periodically by the client interface 
        to receive progress and end results if the input parameter 'wait_for_result' of the related api_request 
        was False. Takes the progress results from APIServer.progress_states put there by 
        APIServer.worker_job_progress() and sends it as response json to the client. When the job is finished the 
        final job result is awaited and taken from the job queue in finalize_request() and sent as response json 
        to the client. 

        Args:
            request (sanic.request.types.Request): Request with client_session_auth_key from client to 
                receive progress and end result 

        Returns:
            sanic.response.types.JSONResponse: Response to client with progress result and end result
        """        

        input_args = request.json if request.method == "POST" else request.args
        job_id, validation_errors = self.validate_progress_request(input_args)

        if validation_errors:
            return self.handle_validation_errors(validation_errors)

        response = {"success": True, 'job_id': job_id, 'ep_version': self.version}
        progress_state = self.get_and_validate_progress_data(job_id)
        job_state = self.app.job_states.get(job_id, JobState.UNKNOWN)
        if job_state == JobState.PROCESSING:
            job_future =  self.app.job_result_futures.get(job_id, None)
            if job_future and job_future.done():
                response['job_result'] = await self.finalize_request(request, job_id, job_future)
                job_state = self.app.job_states.get(job_id, job_state)       

        response['job_state'] = job_state.value
        response['progress'] = progress_state
        APIEndpoint.logger.debug(str(shorten_strings(response)))
        return sanic_json(response)


    async def get_client_session_auth_key(self, request):
        """Route for client interface to login to the API Server while receiving a client session 
        authentication key.

        Args:
            request (sanic.request.types.Request): Request from client.

        Returns:
            sanic.response.types.JSONResponse: Response to client containing the client session authentication key.
        """
        client_session_auth_key = generate_auth_key()
        client_version = request.args.get('version','No version given from client')
        
        self.app.registered_client_sessions[client_session_auth_key] = {self.endpoint_name: 0}

        APIEndpoint.logger.debug(f'Client login with {client_version} on endpoint {self.endpoint_name} in version {self.version}. Assigned session authentication key: {client_session_auth_key}')
        response = {
            'success': True, 
            'ep_version': self.version, 
            'client_session_auth_key': client_session_auth_key
        }
        return sanic_json(response)


    async def init_future_and_put_job_in_worker_queue(self, job_data):
        job_id = job_data.get('job_id')
        APIEndpoint.logger.info(f"Client {job_data.get('client_session_auth_key')} putting job {job_id} into the '{self.worker_job_type}' queue ... ")       
        self.app.job_states[job_id] = JobState.QUEUED
        job_future = asyncio.Future(loop=self.app.loop)
        self.app.job_result_futures[job_id] = job_future

        await self.app.job_queues.get(self.worker_job_type).put(job_data)
        return job_future


    def handle_validation_errors(self, validation_errors):
        response = {'success': False, 'errors': validation_errors, 'ep_version': self.version}
        APIEndpoint.logger.debug(f'Aborted request: {", ".join(validation_errors)}')
        return sanic_json(response, status=400)


    def validate_progress_request(self, input_args):
        validation_errors = []

        client_session_auth_key = input_args.get('client_session_auth_key', None)

        if not client_session_auth_key in self.app.registered_client_sessions:
            validation_errors.append(f'Client session authentication key not registered in API Server')

        job_id = input_args.get('job_id', None)
        if not job_id:
            validation_errors.append(f'No job_id given')

        job_state = self.app.job_states.get(job_id, JobState.UNKNOWN)
        if job_state == JobState.UNKNOWN:
            validation_errors.append(f'Client has no active request with this job id')

        return job_id, validation_errors


    async def finalize_request(self, request, job_id, job_future):
        """Awaits the result until the APIServer.worker_job_result_json() puts the job results in the related future 
        initialized in api_request() to get the results.

        Args:
            request (sanic.request.types.Request): _description_
            job_id (_type_): _description_
            job_future (_type_): _description_

        Returns:
            _type_: _description_
        """        

        response = {'success': True, 'job_id': job_id, 'ep_version': self.version}
        result = await job_future

        #--- extract and store session variables from job
        for ep_session_param_name in self.ep_session_param_config:
            if ep_session_param_name in result:
                request.ctx.session[ep_session_param_name] = result[ep_session_param_name]

        #--- read job outputs
        for ep_output_param_name in self.ep_output_param_config:
            if ep_output_param_name in result:
                APIEndpoint.logger.debug('job outputs: ')
                APIEndpoint.logger.debug(f'{ep_output_param_name}: {shorten_strings(result[ep_output_param_name])}')
                response[ep_output_param_name] = result[ep_output_param_name]
            else:
                if ep_output_param_name != 'error':
                    APIEndpoint.logger.warn(f"missing output '{ep_output_param_name}' in job results")
        meta_outputs = ['compute_duration', 'total_duration', 'auth', 'worker_interface_version']
        queue = self.app.job_queues.get(self.worker_job_type)
        queue.update_mean_job_duration(result)
        if self.provide_worker_meta_data:
            for meta_output in meta_outputs:
                if meta_output in result:
                    response[meta_output] = result[meta_output]

        self.app.job_states[job_id] = JobState.DONE
        self.app.progress_states[job_id] = {}
        return response

    
    def validate_input_parameters_for_job_data(self, input_args, start_time):
        """Check if worker input parameters received from client are as specified in the endpoint config file
        """
        validation_errors = []
        for param in input_args.keys():
            if param not in self.ep_input_param_config:
                validation_errors.append(f'Invalid parameter: {param}')
        job_data = dict()
        for ep_input_param_name in self.ep_input_param_config:
            arg_definition = self.ep_input_param_config[ep_input_param_name]
            arg_required = arg_definition.get('required', False)
            arg_type = arg_definition.get('type', 'string')
            expected_value_type = TYPES_DICT[arg_type]
            value_default = arg_definition.get('default', None)
            value = input_args.get(ep_input_param_name, None)

            if arg_required and value is None:
                validation_errors.append(f'Missing required argument: {ep_input_param_name}')
            if value is not None and not isinstance(value, expected_value_type):
                if expected_value_type is str:
                    validation_errors.append(f'Invalid argument type {ep_input_param_name}. Expected: {expected_value_type} but got {type(value)}')
                else:
                    if not value == float(value) or not value == int(value):
                        validation_errors.append(f'Invalid argument type {ep_input_param_name}. Expected: {expected_value_type} but got {type(value)}')

            if value is not None:
                if isinstance(value, (int, float)):
                    minimum = arg_definition.get('minimum', None)
                    maximum = arg_definition.get('maximum', None)

                    if minimum is not None and value < minimum:
                        validation_errors.append(f'Value for argument {ep_input_param_name} is below the minimum ({minimum})')

                    if maximum is not None and value > maximum:
                        validation_errors.append(f'Value for argument {ep_input_param_name} is above the maximum ({maximum})')
                elif isinstance(value, str):
                    if arg_type == 'image':
                        value = self.rescale_image(value, arg_definition)
                    elif arg_type == 'audio':
                        value = self.convert_audio(value, arg_definition)
                    elif arg_type == 'string':
                        max_length = arg_definition.get('max_length', None)
                        if max_length is not None and len(value) > max_length:
                            validation_errors.append(f'Length of argument {ep_input_param_name} exceeds the maximum length ({max_length})')

                APIEndpoint.logger.debug(f'Received for {ep_input_param_name}: {r"{}".format(shorten_strings(value))}')
                job_data[ep_input_param_name] = value
            elif not arg_required:
                job_data[ep_input_param_name] = value_default

        return job_data, validation_errors


    def add_session_variables_to_job_data(self, request, job_data):
        for ep_session_param_name in self.ep_session_param_config:
            arg_definition = self.ep_session_param_config[ep_session_param_name]
            value_default = arg_definition.get('default', None)
            value = request.ctx.session.get(ep_session_param_name, value_default)
            if value is not None:
                job_data[ep_session_param_name] = value
        return job_data


    def prepare_job_data(self, job_data, start_time):
        job_data['job_id'] = self.app.job_queues[self.worker_job_type].get_next_job_id()
        job_data['endpoint_name'] = self.endpoint_name
        job_data['start_time'] = start_time
        APIEndpoint.logger.debug('Job data: ')
        APIEndpoint.logger.debug(str(shorten_strings(job_data)))
        return job_data


    def validate_client(self, input_args):
        client_session_auth_key = input_args.get('client_session_auth_key')

        validation_errors = []
        if not client_session_auth_key in self.app.registered_client_sessions:
            validation_errors.append(f'Client session authentication key not registered in API Server')
        else:
            self.app.registered_client_sessions[client_session_auth_key][self.endpoint_name] += 1
            if self.client_request_limit and self.app.registered_client_sessions[client_session_auth_key] > self.client_request_limit:
                validation_errors.append(f'Client has too much requests. Only {self.client_request_limit} requests per client allowed.')
        return validation_errors


    def get_and_validate_progress_data(self, job_id):
        progress_state = self.app.progress_states.get(job_id, {})
        queue = self.app.job_queues.get(self.worker_job_type)
        if progress_state:
            
            progress_data_validated = dict()
            progress_data = progress_state.get('progress_data', None)
            if progress_data:
                for ep_progress_param_name in self.ep_progress_param_config:
                    if ep_progress_param_name in progress_data:
                        APIEndpoint.logger.debug('progress outputs: ')
                        APIEndpoint.logger.debug(shorten_strings(progress_data[ep_progress_param_name]))
                        progress_data_validated[ep_progress_param_name] = progress_data[ep_progress_param_name]
            progress_state['progress_data'] = progress_data_validated
        else:
            progress_state['progress'] = 0

        queue_position, estimate, num_workers_online = self.get_queue_parameters(job_id, queue, progress_state)
        progress_state['estimate'] = estimate
        progress_state['queue_position'] = queue_position
        progress_state['num_workers_online'] = num_workers_online
        return progress_state


    def calculate_estimate_time(self, estimate_duration, start_time):
        return round(estimate_duration - (time.time() - start_time), 1)


    def get_queue_parameters(self, job_id, queue, progress_state):
                
        job_state = self.app.job_states.get(job_id, JobState.UNKNOWN)
        queue_position = 0
        queue.update_worker_status()
        num_workers_online = sum(1 for worker in queue.registered_workers.values() if worker.get('status') in ('waiting', 'processing', f'finished job {job_id}'))
        if progress_state['progress'] == 100:
            estimate = 0
        elif job_state == JobState.QUEUED:
            queue_position = queue.get_rank_for_job_id(job_id)
            if num_workers_online and queue_position:                
                estimate = max(
                    self.calculate_estimate_time(
                        queue.mean_job_duration['compute_duration'] * (queue_position + 1) / num_workers_online,
                        queue.get_start_time_for_job_id(job_id)
                    ),
                    self.calculate_estimate_time(
                        queue.mean_job_duration['total_duration'], 
                        queue.get_start_time_for_job_id(job_id))
                )
            else:
                estimate = -1
        elif job_state == JobState.PROCESSING and progress_state and progress_state.get('start_time_compute'):
            estimate = max(
                0,
                self.calculate_estimate_time(
                    queue.mean_job_duration['compute_duration'], 
                    progress_state.get('start_time_compute'))
            )
        else:
            estimate = queue.mean_job_duration['compute_duration']

        return queue_position, estimate, num_workers_online


    def convert_audio(self, base64_string, arg_definition):
        if arg_definition.get('option_auto_convert'):
            header, body = base64_string.split(',')
            audio_bytes = base64.b64decode(body)
            bit_depth_dict = {
                8: 'u8',
                16: 's16',
                32: 's32',
                64: 's64'
            }
            input_duration = self.get_audio_duration(audio_bytes)
            command = [
                'ffmpeg',
                '-i', 'pipe:0',
                '-f', arg_definition.get('audio_format', 'wav'),
                '-ar', str(arg_definition.get('sample_rate', 16000)),
                '-ac', str(arg_definition.get('channels', 1)),
                '-sample_fmt', bit_depth_dict.get(arg_definition.get('sample_bit_depth', 16)),
                'pipe:1'
            ]
            if input_duration > arg_definition.get('max_length', 120):
                command.insert(-1, '-t')
                command.insert(-1, str(arg_definition.get('max_length', 120)))

            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            audio, _ = process.communicate(input=audio_bytes)
            base64_string = f'data:audio/wav;base64,' + base64.b64encode(audio).decode('utf-8')
        return base64_string


    def get_audio_duration(self, audio_bytes):

        try:
            ffprobe_command = ['ffprobe', '-i', 'pipe:0', '-show_entries', 'format=duration', '-v', 'quiet', '-of', 'csv=p=0']
            process = subprocess.Popen(ffprobe_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = process.communicate(input=audio_bytes)
            input_duration = float(result[0].decode().strip())
        except ValueError:
            ffprobe_command = ['ffprobe', '-i', 'pipe:0', '-show_entries', 'format=bit_rate', '-v', 'quiet', '-of', 'csv=p=0']
            process = subprocess.Popen(ffprobe_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = process.communicate(input=audio_bytes)
            bit_rate = float(result[0].decode().strip())
            size = sys.getsizeof(audio_bytes)
            input_duration = size/(bit_rate/8)
        return input_duration
            

    def rescale_image(self, value, arg_definition):
        expected_color_space = arg_definition.get('color_space', 'RGB')
        expected_image_format = arg_definition.get('image_format', 'PNG')
        #original_extension = guess_extension(guess_type(value)[0]).strip('.')
        image = APIEndpoint.convert_base64_string_to_image(value, expected_color_space)
        width, height = APIEndpoint.get_valid_image_size(image, arg_definition)
        if arg_definition.get('option_auto_resize'):
            resize_method = arg_definition.get('option_resize_method', 'scale')
            if resize_method == 'scale':
                image = image.resize((width, height), resample=Image.Resampling.LANCZOS)
            elif resize_method == 'crop':
                image = APIEndpoint.crop_center(image, width, height)
        image_64 = APIEndpoint.convert_image_to_base64_string(image, expected_image_format)
        return image_64


    @staticmethod
    def get_valid_image_size(image, arg_definition):
        min_width = arg_definition.get('min_width', 0)
        max_width = arg_definition.get('max_width', 5000)
        min_height = arg_definition.get('min_height', 0)
        max_height = arg_definition.get('max_height', 5000)
        align_width = arg_definition.get('align_width', 1)
        align_height = arg_definition.get('align_height', 1)
        
        width, height = image.size
        width = min_width if width < min_width else width
        width = max_width if width > max_width else width
        height = min_height if height < min_height else height
        height = max_height if height > max_height else height
        width = width - width % align_width
        height = height - height % align_height
        return width, height

        
    @staticmethod
    def crop_center(image, crop_width, crop_height):
        img_width, img_height = image.size
        left = (img_width - crop_width) / 2
        top = (img_height - crop_height) / 2
        right = (img_width + crop_width) / 2
        bottom = (img_height + crop_height) / 2
        return image.crop((left, top, right, bottom))


    @staticmethod
    def convert_base64_string_to_image(base64_string, expected_color_space):
        base64_data = base64_string.split(',')[1]
        image_data = base64.b64decode(base64_data)
        try:
            with io.BytesIO(image_data) as buffer:
                image = Image.open(buffer).convert(expected_color_space)
                return image.copy()
        except UnidentifiedImageError:
            return pickle.loads(image_data)


    @staticmethod
    def convert_image_to_base64_string(image, expected_image_format):
        with io.BytesIO() as buffer:
            image.save(buffer, format=expected_image_format)
            image_64 = f'data:image/{expected_image_format};base64,' + base64.b64encode(buffer.getvalue()).decode('utf-8')
        return image_64

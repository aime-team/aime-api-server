# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from sanic.log import logging
from sanic.response import json as sanic_json

import urllib.request # Frage an Toine: Benötigt?

import asyncio

import time
from pathlib import Path
import toml

from .job_queue import JobState, WorkerState
from .utils.misc import StaticRouteHandler, JinjaRouteHandler, shorten_strings, generate_auth_key
from .input_validation import InputValidationHandler



TYPES_DICT = {'string': str, 'integer':int, 'float':float, 'bool':bool, 'image':str, 'audio':str}
WORKER_META_PARAMETERS = ['auth', 'worker_interface_version']
STATISTIC_PARAMETERS = [
    'start_time',
    'start_time_compute',
    'arrival_time',
    'finished_time',
    'result_received_time',
    'compute_duration',
    'total_duration',
    'pending_duration',
    'preprocessing_duration'
]



class APIEndpoint():
    """AIME API endpoint

    Args:
        app (APIServer): Instance of APIServer()
        config_file (str): Endpoint config file path.
    """    
    logger = logging.getLogger('API')

    def __init__(self, app, config_file):
        self.app = app
        self.config = self.get_config_from_file(config_file)
        self.title, self.endpoint_name, self.description, self.category, self.http_methods, self.version, self.max_queue_length, self.max_time_in_queue = self.get_endpoint_description()
        self.clients_config = self.config.get('CLIENTS', {})
        self.ep_input_param_config, self.ep_output_param_config, self.ep_progress_param_config, self.ep_session_param_config = self.get_param_config()
        self.ep_input_param_config['client_session_auth_key'] = { 'type': 'string'}     # add implicit input 
        self.ep_input_param_config['key'] = { 'type': 'string'}  # add implicit input 
        self.ep_input_param_config['wait_for_result'] = { 'type': 'bool'}     # add implicit input 
        self.worker_job_type, self.worker_auth_key = self.get_worker_params()
        self.lock = asyncio.Lock()
        self.__status_data = self.init_ep_status_data()

        app.add_route(self.api_request, "/" + self.endpoint_name, methods=self.http_methods, name=self.endpoint_name)
        app.add_route(self.api_progress, "/" + self.endpoint_name + "/progress", methods=self.http_methods, name=self.endpoint_name + "$progress")
        app.add_route(self.client_login, "/" + self.endpoint_name + "/login", methods=self.http_methods, name=self.endpoint_name + "$login")
        app.add_route(self.client_get_endpoint_details, "/api/endpoints/" + self.endpoint_name, methods=self.http_methods, name=self.endpoint_name + "$get_endpoint_details")

        self.add_static_routes(config_file)
        self.add_jinja_routes(config_file)


    def get_config_from_file(self, config_file):
        with open(config_file, 'r') as file:
            endpoint_config = toml.load(file)
        return self.fill_missing_config_with_server_default_config(endpoint_config)


    def fill_missing_config_with_server_default_config(self, endpoint_config):
        for server_config_section_name, server_config_section in self.app.server_config.items():
            default_values = {
                config_name.replace('default_', ''): config_value
                for config_name, config_value in server_config_section.items()
                if config_name.startswith('default_')
            }
            if default_values:
                if server_config_section_name not in endpoint_config and server_config_section_name == 'CLIENTS':
                    endpoint_config[server_config_section_name] = dict()
                elif server_config_section_name[:-1] not in endpoint_config and not server_config_section_name == 'CLIENTS':
                    endpoint_config[server_config_section_name[:-1]] = dict()

                endpoint_config_section = endpoint_config.get(
                    server_config_section_name,
                    endpoint_config.get(server_config_section_name[:-1])
                )
                for config_name, config_value in default_values.items():
                    if config_name not in endpoint_config_section:
                        endpoint_config_section[config_name] = config_value
       
        return endpoint_config


    def add_static_routes(self, config_file):
        config_dir = Path(config_file).parent

        static_files_config = self.config.get('STATIC', {})
        static_route_handler = StaticRouteHandler(config_dir, self.app, self.endpoint_name)
        static_route_handler.setup_static_routes(static_files_config)


    def add_jinja_routes(self, config_file):
        config_dir = Path(config_file).parent

        jinja_files_config = self.config.get('JINJA', {})
        jinja_route_handler = JinjaRouteHandler(
            config_file_path=config_dir,
            app=self.app,
            endpoint_name=self.endpoint_name
        )
        jinja_route_handler.setup_jinja_routes(jinja_files_config)
    
    

    def get_endpoint_description(self):
        """Loads endpoint description parameters title, name, description, http_methods, version
        and max_queue_length and max_time_in_queue from given endpoint config file.

        Args:
            config (dict): Config dictionary

        Returns:
            tuple (str, str, str, list, int, int, int): Tuple with endpoint descriptions title, name, description, http_methods, 
                                                        version, max_queue_length, max_time_in_queue.
        """
        ep_config = self.config['ENDPOINT']
        name = ep_config['name']             
        title = ep_config.get('title', name)  
        http_methods = self.get_http_methods(ep_config)
        APIEndpoint.logger.info(f'----------- {title} - {name} {http_methods}')
        return (
            title,
            name,
            ep_config.get('description', title),
            ep_config.get('category'),
            http_methods,
            ep_config.get('version'),
            ep_config.get('max_queue_length'),
            ep_config.get('max_time_in_queue')
        )
  
   
    def get_http_methods(self, ep_config):
        """Loads http methods defined in given endpoint config file

        Args:
            config (dict): Config dictionary

        Returns:
            list: List of http methods like ['GET', 'POST']
        """
        http_methods = ep_config.get('methods', ['GET', 'POST'])
        for http_method in http_methods:
            if http_method not in ('GET', 'POST'):
                APIEndpoint.logger.error("unknown HTTP method: " + http_method)
        return http_methods


    def get_param_config(self):
        """Parses endpoint input-, output-, progress-, and session-parameter configuration from
        given endpoint config file.

        Args:
            config (dict): Config dictionary

        Returns:
            tuple (dict, dict, dict, dict): Tuple of dictionaries with input-, output-, progress-, 
                and session-parameter configuration
        """
        ep_input_param_config = self.config.get('INPUTS', {})
        ep_output_param_config = self.config.get('OUTPUTS', {})
        ep_progress_param_config = self.config.get('PROGRESS', {})
        ep_session_param_config = self.config.get('SESSION', {}).get(("VARS"), {})
        self.log_parameter_config('Input', ep_input_param_config)
        self.log_parameter_config('Output', ep_output_param_config)
        self.log_parameter_config('Progress output', ep_progress_param_config.get('OUTPUTS', {}), False)

        return ep_input_param_config, ep_output_param_config, ep_progress_param_config, ep_session_param_config

    def log_parameter_config(self, param_type, config, warning=True):
        APIEndpoint.logger.info(f'{param_type} parameter config:')
        if config:
            for param_name, param_value in config.items():
                APIEndpoint.logger.info(f'{param_name}: {param_value}')
        else:
            if warning:
                APIEndpoint.logger.warning('No configuration found')
            else:
                APIEndpoint.logger.info('No configuration found')


    def get_worker_params(self):
        """Parses worker parameters like job type and worker authorization key from endpoint config file.

        Args:
            config (dict): Config dictionary

        Returns:
            tuple (str, str): Tuple of job_type and worker_auth_key
        """
        worker_config = self.config.get('WORKER', {})
        job_type = worker_config.get('job_type')    
        if job_type == None:
            APIEndpoint.logger.error("No job_type for worker configured!")
        else:
            APIEndpoint.logger.info("Worker job type: " + job_type)
        worker_auth_key = worker_config.get('auth_key')
        return job_type, worker_auth_key   


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

        self.__status_data['last_request_time'] = time.time()
        input_args = request.json if request.method == "POST" else request.args
        if self.__status_data.get('enabled'):
            if self.app.job_handler.get_free_queue_slots(self.endpoint_name):
                self.__status_data['num_requests'] += 1

                validation_errors, error_code = await self.validate_client(request)

                if not validation_errors:
                    job_data, validation_errors = await self.validate_input_parameters_for_job_data(input_args)
                    if not validation_errors:
                        job_data = self.add_session_variables_to_job_data(request, job_data)
                        job_data['endpoint_name'] = self.endpoint_name

                        job = await self.app.job_handler.endpoint_new_job(job_data)
                        if self.app.admin_backend:
                            await self.app.admin_backend.admin_log_request_start(
                                job.id,
                                input_args.get('key') or self.app.registered_keys.get(input_args.get('client_session_auth_key')),
                                self.endpoint_name,
                                request.path,
                                job.start_time,
                                await job.state,
                                request.headers.get('x-forwarded-for') or request.ip,
                                dict(request.headers)
                            )
                        if input_args.get('wait_for_result', True):
                            response = await self.finalize_request(request, job) 
                        else:
                            response = {
                                'success': True,
                                'job_id': job.id,
                                'ep_version': self.version
                            }
                        APIEndpoint.logger.debug(f'Response to client on /{self.endpoint_name}: {str(shorten_strings(response))}')
                    else:
                        error_code = 400 # TODO Define error code for invalid input parameters
                else:
                    self.__status_data['num_unauthorized_requests'] += 1
            else:
                validation_errors = f'Job queue reached max length {self.max_queue_length}!'
                error_code = 400 # # TODO Define error code for Full job queue
        else:
            validation_errors = 'Endpoint disabled!'
            error_code = 400 # # TODO Define error code for disabled endpoint
            

        if validation_errors:
            self.__status_data['num_invalid_requests'] += 1
            response = {'success': False, 'error': validation_errors, 'ep_version': self.version}
            if isinstance(validation_errors, list):
                validation_errors = ', '.join(error_msg for error_msg in validation_errors)
            APIEndpoint.logger.warning(f'Aborted request on endpoint {self.endpoint_name}: {validation_errors}')
            if self.app.admin_backend:
                await self.app.admin_backend.admin_log_invalid_request(
                    input_args.get('key') or self.app.registered_keys.get(input_args.get('client_session_auth_key')),
                    'request',
                    self.endpoint_name,
                    time.time(),
                    validation_errors,
                    request.headers.get('x-forwarded-for') or request.ip,
                    dict(request.headers)
                )
            return sanic_json(response, status=error_code)

        return sanic_json(response)

    async def process_api_progress(self, request, job):
        response = {"success": True, 'job_id': job.id, 'ep_version': self.version}
        error_code = 200
        if await job.state == JobState.PROCESSING:
            if self.app.job_handler.is_job_future_done(job):
                response['job_result'] = await self.finalize_request(request, job)
                APIEndpoint.logger.debug(f'Final response to client on /{self.endpoint_name}/progress: {str(shorten_strings(response))}')
        elif await job.state == JobState.LAPSED:
            error_code = 400 # Define error code for lapsed job
            response = await self.handle_invalid_progress_request(f'Job {job.id} on {self.endpoint_name} lapsed!', request)
        response['job_state'] = await job.state
        if await job.state != JobState.DONE:
            response['progress'] = await self.get_and_validate_progress_data(job)
        return response, error_code

    async def api_progress(self, request):
        """Client request on route /self.endpoint_name/progress called periodically by the client interface 
        to receive progress and end results if the input parameter 'wait_for_result' of the related api_request 
        was False. Takes the progress results from APIServer.job_handler.progress_states put there by 
        APIServer.worker_job_progress() and sends it as response json to the client. When the job is finished the 
        final job result is awaited and taken from the job queue in finalize_request() and sent as response json 
        to the client. 

        Args:
            request (sanic.request.types.Request): Request with client_session_auth_key from client to 
                receive progress and end result 

        Returns:
            sanic.response.types.JSONResponse: Response to client with progress result and end result
        """        
        
        validation_errors, error_code = await self.validate_progress_request(request)
        if validation_errors:
            response = await self.handle_invalid_progress_request(validation_errors, request)
        else:
            input_args = request.json if request.method == "POST" else request.args
            job = self.app.job_handler.get_job(input_args.get('job_id'))
            response, error_code = await self.process_api_progress(request, job)
        return sanic_json(response, status=error_code)


    async def client_login(self, request):
        """Route for client interface to login to the API Server while receiving a client session 
        authentication key.
        Args:
            request (sanic.request.types.Request): Request from client.
        Returns:
            sanic.response.types.JSONResponse: Response to client containing the client session authentication key.
        """
        api_key = request.args.get('key', None)
        if self.app.admin_backend:
            response = await self.app.admin_backend.admin_is_api_key_valid(
                api_key,
                request.headers.get('x-forwarded-for') or request.ip
                )
            if not response.get('valid'):
                return sanic_json(
                    {
                        'success': False,
                        'error': response.get('error_msg'),
                    }
                )
        client_session_auth_key = generate_auth_key()
        client_version = request.args.get('version','No version given from client')
        self.app.registered_keys[client_session_auth_key] = api_key
        APIEndpoint.logger.debug(f'Client login with {client_version} on endpoint {self.endpoint_name} in version {self.version}. Assigned session authentication key: {client_session_auth_key}')
        return sanic_json(
            {
                'success': True, 
                'ep_version': self.version, 
                'client_session_auth_key': client_session_auth_key,
                'key': api_key
            }
        )


    async def client_get_endpoint_details(self, request):
        """Route /api/endpoints/<endpoint_name> to get details about <endpoint_name>. 

        Args:
            request (sanic.request.types.Request): Client request

        Returns:
            sanic.response.types.JSONResponse: Response to client. Example: 
            {
                'name': 'llama3_chat', 
                'title': 'LLama 3.x Chat',
                'description': 'Llama 3.x Instruct Chat example API',
                'http_methods': ['GET', 'POST'],
                'version': 2,
                'max_queue_length': 1000,
                'max_time_in_queue': 3600,
                'free_queue_slots': 1000,
                'category': 'chat',
                'num_active_workers': 1,
                'num_workers': 1,
                'workers': [
                    {
                        'name': 'hostname#0_2xNVIDIA_GeForce_RTX_3090',
                        'state': 'waiting',
                        'max_batch_size': 128,
                        'free_slots': 128,
                        'model': {
                            'label': 'Meta-Llama-3-8B-Instruct',
                            'quantization': 'fp16',
                            'size': '8B',
                            'family': 'Llama',
                            'type': 'LLM',
                            'repo_name': 'Meta-Llama-3-8B-Instruct'
                        }
                    }
                ],
                'parameter_description': {
                    'input': {
                        'prompt_input': {'type': 'string', 'default': '', 'required': False},
                        'chat_context': {'type': 'json', 'default': '', 'required': False},
                        'top_k': {'type': 'integer', 'minimum': 1, 'maximum': 1000, 'default': 40},
                        'top_p': {'type': 'float', 'minimum': 0.0, 'maximum': 1.0, 'default': 0.9},
                        'temperature': {'type': 'float', 'minimum': 0.0, 'maximum': 1.0, 'default': 0.8},
                        'max_gen_tokens': {'type': 'integer', 'default': 2000},
                        'client_session_auth_key': {'type': 'string'},
                        'key': {'type': 'string'},
                        'wait_for_result': {'type': 'bool'}
                    },
                    'output': {
                        'text': {'type': 'string'},
                        'num_generated_tokens': {'type': 'integer'},
                        'model_name': {'type': 'string'},
                        'max_seq_len': {'type': 'integer'},
                        'current_context_length': {'type': 'integer'},
                        'error': {'type': 'string'},
                        'prompt_length': {'type': 'integer'}
                    },
                    'progress': {
                        'OUTPUTS': {
                            'text': {'type': 'string'},
                            'num_generated_tokens': {'type': 'integer'},
                            'current_context_length': {'type': 'integer'}
                        }
                    }
                }
            }

        """        
        workers = await self.app.job_handler.get_all_workers(self.worker_job_type)
        return sanic_json(
            {
                'name': self.endpoint_name,
                'title': self.title,
                'description': self.description,
                'http_methods': self.http_methods,
                'version': self.version,
                'max_queue_length': self.max_queue_length,
                'max_time_in_queue': self.max_time_in_queue,
                'free_queue_slots': self.app.job_handler.get_free_queue_slots(self.endpoint_name),
                'category': self.category,
                'num_active_workers': len(await self.app.job_handler.get_all_active_workers(self.worker_job_type)),
                'num_workers': len(workers),
                'workers': [
                    {
                        'name': worker.auth,
                        'state': worker.state,
                        'max_batch_size': worker.max_batch_size,
                        'free_slots': worker.free_slots,
                        'gpu_name': worker.gpu_name,
                        'num_gpus': worker.num_gpus,
                        'framework':  worker.framework,
                        'framework_version': worker.framework_version,
                        'pytorch_version':  worker.pytorch_version,
                        'model': vars(worker.model),
                        
                    }
                    for worker in workers
                ],
                'parameter_description': {
                    'input': self.ep_input_param_config,
                    'output': self.ep_output_param_config,
                    'progress': self.ep_progress_param_config
                }
            }
        )


    async def handle_invalid_progress_request(self, validation_errors, request):
        input_args = request.json if request.method == "POST" else request.args
        self.__status_data['num_invalid_progress_requests'] += 1
        response = {'success': False, 'error': validation_errors, 'ep_version': self.version}
        if isinstance(validation_errors, list):
            validation_errors = ', '.join(error_msg for error_msg in validation_errors)
        APIEndpoint.logger.warning(f'Aborted progress request on endpoint {self.endpoint_name}: {validation_errors}')
        await self.app.admin_backend.admin_log_invalid_request(
            input_args.get('key') or self.app.registered_keys.get(input_args.get('client_session_auth_key')),
            'progress_request',
            self.endpoint_name,
            time.time(),
            validation_errors,
            request.headers.get('x-forwarded-for') or request.ip,
            dict(request.headers)
        )

        return response


    async def validate_progress_request(self, request):
        validation_errors = list()
        error_code = None
        input_args = request.json if request.method == "POST" else request.args
        job_id = input_args.get('job_id')
        if not job_id:
            validation_errors.append(f'No job_id given')
            error_code = 402 # TODO Define error codes for missing job id
        elif not self.app.job_handler.get_job(job_id):
            validation_errors.append(f'Client has no active request with this job id {job_id}')
            error_code = 402 # TODO Define error codes for invalid job id
        return validation_errors, error_code


    async def finalize_request(self, request, job):
        """Awaits the result until the APIServer.worker_job_result_json() puts the job results in the related future 
        initialized in api_request() to get the results.

        Args:
            request (sanic.request.types.Request): _description_
            job (Job): Instance of class Job()

        Returns:
            dict: Dictionary representation of the response.
        """        
        result = await self.app.job_handler.endpoint_wait_for_job_result(job)
        response = {'success': True, 'job_id': job.id, 'ep_version': self.version}

        #--- extract and store session variables from job
        for ep_session_param_name in self.ep_session_param_config:
            if ep_session_param_name in result:
                request.ctx.session[ep_session_param_name] = result[ep_session_param_name]

        #--- read job outputs
        for ep_output_param_name in self.ep_output_param_config:
            if ep_output_param_name in result:
                response[ep_output_param_name] = result[ep_output_param_name]
            else:
                if ep_output_param_name != 'error':
                    APIEndpoint.logger.warn(f"missing output '{ep_output_param_name}' in job results")

        if self.clients_config.get('provide_worker_meta_data'):
            response.update({key: result[key] for key in WORKER_META_PARAMETERS if key in result})
        response.update({key: result[key] for key in STATISTIC_PARAMETERS if key in result})
        self.__status_data['num_finished_requests'] += 1
        return response


    async def validate_input_parameters_for_job_data(self, input_args):
        """Check if worker input parameters received from client are as specified in the endpoint config file
        """
        input_validator = InputValidationHandler(input_args, self.ep_input_param_config, self.app.input_param_config)
        return await input_validator.validate_input_parameters()
           

    def add_session_variables_to_job_data(self, request, job_data):
        for ep_session_param_name in self.ep_session_param_config:
            arg_definition = self.ep_session_param_config[ep_session_param_name]
            value_default = arg_definition.get('default', None)
            value = request.ctx.session.get(ep_session_param_name, value_default)
            if value is not None:
                job_data[ep_session_param_name] = value
        return job_data


    async def validate_client(self, request):
        input_args = request.json if request.method == "POST" else request.args
        api_key = input_args.get('key')
        client_session_auth_key = input_args.get('client_session_auth_key')
        error_code = None
        validation_errors = []
        if self.app.admin_backend:
            if api_key:
                response = await self.app.admin_backend.admin_is_api_key_valid(
                    api_key,
                    request.headers.get('x-forwarded-for') or request.ip
                )
                if not response.get('valid'):
                    validation_errors.append(response.get('error_msg') or 'API key not valid')
                    error_code = 401 # TODO Define error codes for invalid key
                elif not await self.app.admin_backend.admin_is_api_key_authorized_for_endpoint(api_key, self.endpoint_name):
                    validation_errors.append(f'Client not authorized for endpoint {self.endpoint_name}!')
                    error_code = 402 # TODO Define error codes for unauthorized endpoint
            elif client_session_auth_key not in self.app.registered_keys:
                validation_errors.append(f'API Key missing and client session authentication key not registered in API Server')
                error_code = 401

        return validation_errors, error_code


    async def get_and_validate_progress_data(self, job_id):
        progress_state = await self.app.job_handler.endpoint_get_progress_state(job_id)
        if progress_state:          
            progress_data_validated = dict()
            progress_data = progress_state.get('progress_data', None)
            if progress_data:
                for ep_progress_output_param_name in self.ep_progress_param_config.get('OUTPUTS'):
                    if ep_progress_output_param_name in progress_data:
                        progress_data_validated[ep_progress_output_param_name] = progress_data[ep_progress_output_param_name]
            progress_state['progress_data'] = progress_data_validated

        return progress_state


    def init_ep_status_data(self):
        status_data = {
            'last_request_time': None,
            'num_requests': 0,
            'num_finished_requests': 0,
            'num_invalid_requests': 0,
            'num_invalid_progress_requests': 0,
            'num_failed_requests': 0,
            'num_unauthorized_requests': 0,
            'num_canceled_requests': 0,
            'enabled': True
        }
        return status_data


    @property
    async def status_data(self):
        self.__status_data.update(await self.app.job_handler.get_job_type_status(self.worker_job_type))
        return self.__status_data


    @property
    def status_data_sync(self):
        return self.__status_data

    def enable(self):
        self.__status_data['enabled'] = True


    def disable(self):
        self.__status_data['enabled'] = False


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

from .job_queue import JobState
from .utils.misc import StaticRouteHandler, shorten_strings, generate_auth_key
from .input_validation import InputValidationHandler



TYPES_DICT = {'string': str, 'integer':int, 'float':float, 'bool':bool, 'image':str, 'audio':str}

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
        self.title, self.endpoint_name, self.description, self.http_methods, self.version = self.get_endpoint_description()
        self.client_request_limit, self.provide_worker_meta_data, self.authentication, self.authorization, self.authorization_keys = self.get_clients_config()
        self.ep_input_param_config, self.ep_output_param_config, self.ep_progress_param_config, self.ep_session_param_config = self.get_param_config()
        self.ep_input_param_config['client_session_auth_key'] = { 'type': 'string'}     # add implicit input 
        self.ep_input_param_config['wait_for_result'] = { 'type': 'bool'}     # add implicit input 
        self.worker_job_type, self.worker_auth_key = self.get_worker_params()
        self.registered_client_session_auth_keys = dict()
        self.lock = asyncio.Lock()
        self.status_data = self.init_ep_status_data()

        app.add_route(self.api_request, "/" + self.endpoint_name, methods=self.http_methods, name=self.endpoint_name)
        app.add_route(self.api_progress, "/" + self.endpoint_name + "/progress", methods=self.http_methods, name=self.endpoint_name + "$progress")
        app.add_route(self.client_login, "/" + self.endpoint_name + "/login", methods=self.http_methods, name=self.endpoint_name + "$login")

        self.add_static_routes(config_file)


    def init_ep_status_data(self):
        return {
            'last_request_time': None,
            'num_requests': 0,
            'num_finished_requests': 0,
            'num_failed_requests': 0,
            'num_unauthorized_requests': 0,
            'num_canceled_requests': 0
        }

       
    def get_config_from_file(self, config_file):
        with open(config_file, 'r') as file:
            return toml.load(file)


    def add_static_routes(self, config_file):
        static_files_config = self.config.get('STATIC', {})
        static_route_handler = StaticRouteHandler(Path(config_file).parent, self.app, self.endpoint_name)
        static_route_handler.setup_static_routes(static_files_config)


    def get_endpoint_description(self):
        """Loads endpoint description parameters title, name, description, client_request_limit, http_methods from given endpoint config file.

        Args:
            config (dict): Config dictionary

        Returns:
            tuple (str, str, str, int, list): Tuple with endpoint descriptions title, name, description, client_request_limit, http_methods.
        """
        ep_config = self.config['ENDPOINT']
        name = ep_config['name']             
        title = ep_config.get('title', name)  
        description = ep_config.get('description', title)

        http_methods = self.get_http_methods(ep_config)
        version = ep_config.get('version')
        APIEndpoint.logger.info(f'----------- {title} - {name} {http_methods}')
        return title, name, description, http_methods, version


    def get_clients_config(self):
        clients_config = self.config.get('CLIENTS', {})
        if not 'client_request_limit' in clients_config:
            clients_config['client_request_limit'] = self.app.default_client_request_limit

        if not 'provide_worker_meta_data' in clients_config:
            clients_config['provide_worker_meta_data'] = self.app.default_provide_worker_meta_data

        if not 'authentication' in clients_config:
            clients_config['authentication'] = self.app.default_authentication

        if not 'authorization' in clients_config:
            clients_config['authorization'] = self.app.default_authorization

        if not 'authorization_keys' in clients_config:
            clients_config['authorization_keys'] = self.app.default_authorization_keys
        return clients_config['client_request_limit'], clients_config['provide_worker_meta_data'], clients_config['authentication'], clients_config['authorization'], clients_config['authorization_keys']
   
   
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
        worker_auth_key = worker_config.get('auth_key', self.app.worker_config.get('default_auth_key'))
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
        self.status_data['last_request_time'] = time.time()
        self.status_data['num_requests'] += 1
        input_args = request.json if request.method == "POST" else request.args
        validation_errors, error_code = self.validate_client(input_args)

        # fast exit if not authorized for request
        if validation_errors:
            self.status_data['num_unauthorized_requests'] += 1
            return self.handle_validation_errors(validation_errors, error_code)
        job_data, validation_errors = await self.validate_input_parameters_for_job_data(input_args)
        if validation_errors:
            self.status_data['num_failed_requests'] += 1
            return self.handle_validation_errors(validation_errors)

        job_data = self.add_session_variables_to_job_data(request, job_data)
        job_data['endpoint_name'] = self.endpoint_name
        job_id = await self.app.job_type_interface.new_job(job_data)

        if input_args.get('wait_for_result', True):
            response = await self.finalize_request(request, job_id) 
        else:
            response = {'success': True, 'job_id': job_id, 'ep_version': self.version}
        APIEndpoint.logger.debug(f'Response to client on /{self.endpoint_name}: {str(shorten_strings(response))}')
        return sanic_json(response)


    async def api_progress(self, request):
        """Client request on route /self.endpoint_name/progress called periodically by the client interface 
        to receive progress and end results if the input parameter 'wait_for_result' of the related api_request 
        was False. Takes the progress results from APIServer.job_type_interface.progress_states put there by 
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
        job_state = self.app.job_type_interface.get_job_state(job_id)
        
        if job_state == JobState.PROCESSING:
            if self.app.job_type_interface.is_job_future_done(job_id):
                response['job_result'] = await self.finalize_request(request, job_id)
                APIEndpoint.logger.debug(f'Final response to client on /{self.endpoint_name}/progress: {str(shorten_strings(response))}')
                job_state = self.app.job_type_interface.get_job_state(job_id)
        response['job_state'] = job_state.value
        if job_state != JobState.DONE:
            response['progress'] = await self.get_and_validate_progress_data(job_id)
        APIEndpoint.logger.debug(f'Progress response to client on /{self.endpoint_name}/progress: {str(shorten_strings(response))}')
        return sanic_json(response)


    async def client_login(self, request):
        """Route for client interface to login to the API Server while receiving a client session 
        authentication key.
        Args:
            request (sanic.request.types.Request): Request from client.
        Returns:
            sanic.response.types.JSONResponse: Response to client containing the client session authentication key.
        """
        user = request.args.get('user', None)
        key = request.args.get('key', None)

        authorization_error = None

        if self.authentication == 'None':
            pass
        elif self.authentication == 'User':
            if self.authorization == 'None':
                pass
            elif self.authorization == 'Key':
                if user in self.authorization_keys:
                    if key != self.authorization_keys[user]:
                        authorization_error = 'authorization failed'
                else:
                    authorization_error = 'authentication failed'
            else:
                authorization_error = 'unknown authorization method'                
        else:
            authorization_error = 'unknown authentication method'

        if authorization_error:
            response = {
                'success': False,
                'error': authorization_error,
            }
            return sanic_json(response)

        client_session_auth_key = generate_auth_key()
        client_version = request.args.get('version','No version given from client')

        self.app.registered_client_sessions[client_session_auth_key] = {self.endpoint_name: 0}

        APIEndpoint.logger.debug(f'Client login with {client_version} on endpoint {self.endpoint_name} in version {self.version}. Assigned session authentication key: {client_session_auth_key}')
        response = {
            'success': True, 
            'ep_version': self.version, 
            'client_session_auth_key': client_session_auth_key,
            'user': user,
            'key': key

        }
        return sanic_json(response)


    def handle_validation_errors(self, validation_errors, error_code=400):
        response = {'success': False, 'error': validation_errors, 'ep_version': self.version}
        APIEndpoint.logger.warning(f'Aborted request on endpoint {self.endpoint_name}: {", ".join(validation_errors)}')
        return sanic_json(response, status=error_code)


    def validate_progress_request(self, input_args):
        validation_errors = []

        client_session_auth_key = input_args.get('client_session_auth_key', None)

        if not client_session_auth_key in self.app.registered_client_sessions:
            validation_errors.append(f'Client session authentication key not registered in API Server')

        job_id = input_args.get('job_id', None)
        if not job_id:
            validation_errors.append(f'No job_id given')

        if self.app.job_type_interface.get_job_state(job_id) == JobState.UNKNOWN:
            validation_errors.append(f'Client has no active request with this job id')

        return job_id, validation_errors


    async def finalize_request(self, request, job_id):
        """Awaits the result until the APIServer.worker_job_result_json() puts the job results in the related future 
        initialized in api_request() to get the results.

        Args:
            request (sanic.request.types.Request): _description_
            job_id (_type_): _description_
            job_future (_type_): _description_

        Returns:
            dict: Dictionary representation of the response.
        """        
        result = await self.app.job_type_interface.wait_for_job_result()
        response = {'success': True, 'job_id': job_id, 'ep_version': self.version}
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

        meta_outputs = [
            'compute_duration',
            'total_duration',
            'start_time',
            'start_time_compute',
            'auth',
            'worker_interface_version',
            'pending_duration',
            'preprocessing_duration',
            'arrival_time',
            'finished_time',
            'result_received_time'
        ]
        response['result_sent_time'] = time.time()
        if self.provide_worker_meta_data:
            for meta_output in meta_outputs:
                if meta_output in result:
                    response[meta_output] = result[meta_output]
        self.status_data['num_finished_requests'] += 1

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


    def validate_client(self, input_args):
        client_session_auth_key = input_args.get('client_session_auth_key')
        error_code = None
        validation_errors = []
        if not client_session_auth_key in self.app.registered_client_sessions:
            validation_errors.append(f'Client session authentication key not registered in API Server')
            error_code = 401
        else:
            self.app.registered_client_sessions[client_session_auth_key][self.endpoint_name] += 1
            if self.client_request_limit and self.app.registered_client_sessions[client_session_auth_key] > self.client_request_limit:
                validation_errors.append(f'Client has too much requests. Only {self.client_request_limit} requests per client allowed.')
                error_code = 402
        return validation_errors, error_code


    async def get_and_validate_progress_data(self, job_id):
        progress_state = await self.app.job_type_interface.get_progress_state(job_id)
        if progress_state:          
            progress_data_validated = dict()
            progress_data = progress_state.get('progress_data', None)
            if progress_data:
                for ep_progress_output_param_name in self.ep_progress_param_config.get('OUTPUTS'):
                    if ep_progress_output_param_name in progress_data:
                        progress_data_validated[ep_progress_output_param_name] = progress_data[ep_progress_output_param_name]
            progress_state['progress_data'] = progress_data_validated

        return progress_state


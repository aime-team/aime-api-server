from sanic import Sanic
from sanic import response as sanic_response

from sanic.response import json as sanic_json
from sanic.log import logging

from sanic_sass import SassManifest

from http import HTTPStatus
import os
import time
import pathlib
import toml
import urllib.request
import json
import uuid
import asyncio

from .api_endpoint import APIEndpoint, shorten_strings
from .job_queue import JobQueue, JobState
from .markdown_compiler import MarkDownCompiler



logging.getLogger('asyncio').setLevel(logging.ERROR)


class APIServer(Sanic):
    """AIME ML API Server

    Args:
        api_name (str): Name of API server
        args (argparse.Namespace): Command line arguments parsed with argparse

    """
    job_queues = {} # key: endpoint_name
    endpoints = {}  # key: endpoint_name
    job_states = {} # key: job_id
    job_result_futures = {} # key: job_id
    progress_states = {}    # key: job_id
    registered_client_sessions = {} # key: client_session_auth_key
    args = None
    static_routes = {}
    default_authentification = "None"
    default_authorization = "None"
    default_authorization_keys = {}
    logger = logging.getLogger('API')


    def __init__(self, api_name, args):
        """Constructor

        Args:
            api_name (str): Name of API server
            args (argparse.Namespace): Command line arguments parsed with argparse
        """
        
        APIServer.args = args
        self.configure_logger()
        super().__init__(api_name, configure_logging=not args.no_sanic_logger)      
        self.init(args)
        

    async def worker_job_request_json(self, request):
        """Request from API worker interface for a job on route /worker_job_request. If the worker is validated and a job is put in the job_queue
        within job_timeout the job data including 'cmd': 'job' is received from the job queue and send to API worker interface in the json response. 
        If there is no job put in the within job_timeout 'cmd': 'no_job' is 
        received from the job queue and send to API worker interface in the json response. If the validation failed 'cmd': 'error', or 'warning' with
        'msg' is sent to API worker interface.

        Args:
            request (sanic.request.types.Request): Job request from API worker interface on route /worker_job_request.

        Returns:
            sanic.response.types.JSONResponse: Response to API worker interface with job data or messages.

        Examples:

            Example response json if client requested job:

            .. highlight:: python
            .. code-block:: python 

                response.json() = {   
                    'prompt': 'prompt', 
                    'cmd': 'job',
                    'job_id': 'JID1', 
                    'start_time_compute': 1700424731.9582381
                    'start_time': 1700424731.952994, 
                    'wait_for_result': False, 
                    'endpoint_name': 'stable_diffusion_xl_txt2img',     
                    'progress_descriptions' = {
                        'progress_images': {
                            'type': 'image_list',
                            'image_format': 'JPEG',
                            'color_space': 'RGB'
                        }
                    }
                    'output_descriptions' = {
                        'images': {
                            'type': 'image_list',
                            'image_format': 'JPEG',
                            'color_space': 'RGB'
                        },
                        'seed': {'type': 'integer'},
                        'prompt': {'type': 'string'}, 
                        'error': {'type': 'string'}
                    }

                }

            Example response json if no client requested job within job_timeout:
            
            .. highlight:: python
            .. code-block:: python 

                response.json() = {
                    'cmd': 'no_job',
                }

            Example response json if AIME ML API replied with error:
            
            .. highlight:: python
            .. code-block:: python 
            
                response.json() = {
                    'cmd': 'error',
                    'msg': 'Message'
                }

            Example response json if AIME ML API replied with warning:
            
            .. highlight:: python
            .. code-block:: python 

                response.json() = {
                    'cmd': 'warning',
                    'msg': 'Message'
                }
        """
        req_json = request.json
        APIServer.logger.debug(req_json)
        queue = APIServer.job_queues.get(req_json.get('job_type'))
        job_cmd = await self.validate_worker_queue(queue, req_json)
        if job_cmd['cmd'] not in ('ok', 'warning'):
            return sanic_json(job_cmd)
             
        job_data = await self.wait_for_valid_job(queue, req_json)
        return sanic_json(job_data)


    async def worker_job_result_json(self, request):
        """Receive final job result from API worker interface via route /worker_job_result.
        Processes the result and puts it to the future related to the job initialized in APIEndpoint.api_request
        to make it available by APIEndpoint.api_request and APIEndpoint.api_progress to send it to the client.

        Args:
            request (sanic.request.types.Request): API worker interface request containing the job results.

        Returns:
            sanic.response.types.JSONResponse: Response to API worker interface with 'cmd': 'ok' when API server received data.
        """
        result = self.process_job_result(request)
        job_id = result.get('job_id')
        try:
            APIServer.job_result_futures.get(job_id).set_result(result)
        except KeyError:
            job_id = 'unknown job'
        APIServer.logger.info(f"{result.get('auth')}... processed job {job_id}")
        response = {'cmd': 'ok'}
        return sanic_json(response)

    
    def process_job_result(self, request):
        req_json = request.json
        job_id = req_json['job_id']
        req_json['total_duration'] = round(time.time() - req_json.get('start_time'), 1)
        req_json['compute_duration'] = round(time.time() - req_json.pop('start_time_compute'), 1)
        queue = APIServer.job_queues.get(req_json.get('job_type'))
        worker = queue.registered_workers.get(req_json.get('auth'))
        if worker:
            worker['status'] = f'finished job {job_id}'
            worker['jobs_done'] += 1
        if req_json.get('version'):
            req_json['worker_interface_version'] = req_json.pop('version')
        return req_json


    async def worker_job_progress(self, request):
        """Receive progress results from api worker interface via route /worker_job_progress 
        and put it to APIServer.progress_states[job_id] to make it available for APIEndpoint.api_progress(). 

        Args:
            request (sanic.request.types.Request): API worker interface request containing progress results

        Returns:
            sanic.response.types.JSONResponse: Response to API worker interface with 'cmd': 'ok' when API server received data.


        Examples:

            Examples request payload from API worker interface:

            .. highlight:: python
            .. code-block:: python 

                request.json = {    
                    'job_id': 'JID1',
                    'progress': 50,
                    'progress_data': {'progress_images': ['base64-string', 'base64-string', ...]},
                    'start_time_compute': 1700424731.9582381,
                    'start_time': 1700424731.952994
                }
        """
        req_json = request.json
        job_id = req_json.get('job_id')
        APIServer.progress_states[job_id] = req_json
        result = {'cmd': 'ok'}
        return sanic_json(result)


    async def worker_check_server_status(self, request):
        """Route /worker_check_server_status for API worker interface to check
        server connection and queue validation for given job type and worker authentication.

        Args:
            request (sanic.request.types.Request): API worker interface request containing worker validation

        Returns:
            sanic.response.types.JSONResponse: _description_

        Examples:

            Example successful response json to API worker interface:

            .. highlight:: python
            .. code-block:: python 

                response.json() = {'cmd': 'ok'}

            Example response json if AIME ML API replied with warning:

            .. highlight:: python
            .. code-block:: python 

                response.json() = {
                    'cmd': 'error',
                    'msg': 'Message'
                }

            Example response json if AIME ML API replied with warning:
            
            .. highlight:: python
            .. code-block:: python

                response.json() = {
                    'cmd': 'warning',
                    'msg': 'Message'
                }
        """
        req_json = request.json

        if APIServer.job_queues and req_json:
            queue = APIServer.job_queues.get(req_json.get('job_type'))
            req_json['status_check'] = True
            result = await self.validate_worker_queue(queue, req_json)
        else:
            result = { 'cmd': "warning", 'msg': 'Api server still initializing'}
        return sanic_json(result)


    async def get_client_session_auth_key(self, request):
        """Route for client interface to login to the API Server while receiving a client session 
        authentication key.

        Args:
            request (sanic.request.types.Request): _description_

        Returns:
            dict: Dictionary with the client session authentication key
        """
        client_session_auth_key = APIServer.generate_auth_key()
        client_session_endpoint_name = request.args.get('endpoint_name','No_endpoint_given_from_client')
        client_version = request.args.get('version','No version given from client')
        APIServer.logger.debug(f'Client login {client_version} with session auth key {client_session_auth_key} on endpoint {client_session_endpoint_name}')
        self.registered_client_sessions[client_session_auth_key] = client_session_endpoint_name
        for endpoint in APIServer.endpoints.values():
            if endpoint.endpoint_name == client_session_endpoint_name:
                endpoint.registered_client_session_auth_keys[client_session_auth_key] = 0
        return sanic_json({'client_session_auth_key': client_session_auth_key}) # TODO: error handling


    def load_server_configuration(self, app):
        """Parses server configuration file.
        """
        config_file = APIServer.args.server_config
        APIServer.logger.info("Reading server config: " + str(config_file))

        config = {}
        with open(config_file, "r") as f:
            config = toml.load(f)

        clients_config = config.get('CLIENTS', {})
        APIServer.default_authentification = clients_config.get("default_authentification", "None")
        APIServer.default_authorization = clients_config.get("default_authorization", "None")
        APIServer.default_authorization_keys = clients_config.get("default_authorization_keys", {})

        APIServer.static_routes = config.get('STATIC', {})

    def get_endpoint_descriptions(self, config):
        """Loads endpoint description parameters title, name, description, client_request_limit, http_methods from given endpoint config file.

        Args:
            config (dict): Config dictionary

        Returns:
            tuple (str, str, str, int, list): Tuple with endpoint descriptions title, name, description, client_request_limit, http_methods.
        """
        name = config['ENDPOINT']['name']             
        title = config['ENDPOINT'].get('title', name)  
        description = config['ENDPOINT'].get('description', title)
        client_request_limit = config['ENDPOINT'].get('client_request_limit', 0)
        provide_worker_meta_data = config['ENDPOINT'].get('provide_worker_meta_data', False)
        http_methods = self.get_http_methods(config)               
        APIServer.logger.info(f'----------- {title} - {name} {http_methods}')
        return title, name, description, client_request_limit, provide_worker_meta_data, http_methods


    def get_http_methods(self, config):
        """Loads http methods defined in given endpoint config file

        Args:
            config (dict): Config dictionary

        Returns:
            list: List of http methods like ['GET', 'POST']
        """
        http_methods_str = config['ENDPOINT'].get('methods', "GET, POST")
        http_methods = []
        for http_method in http_methods_str.replace(" ", "").split(","):
            if http_method == "GET":
                http_methods.append("GET")
            elif http_method == "POST":
                http_methods.append("POST")
            else:
                APIServer.logger.error("unknown HTTP method: " + http_method)
        return http_methods


    def get_param_config(self, config):
        """Parses endpoint input-, output-, progress-, and session-parameter configuration from
        given endpoint config file.

        Args:
            config (dict): Config dictionary

        Returns:
            tuple (dict, dict, dict, dict): Tuple of dictionaries with input-, output-, progress-, 
                and session-parameter configuration
        """
        ep_input_param_config = config.get('INPUTS', {})
        ep_output_param_config = config.get('OUTPUTS', {})
        ep_progress_param_config = config.get('PROGRESS', {})
        ep_session_param_config = config.get('SESSION', {}).get(("VARS"), {})

        for ep_input_param_name in ep_input_param_config:
            APIServer.logger.debug(str(ep_input_param_name))

        return ep_input_param_config, ep_output_param_config, ep_progress_param_config, ep_session_param_config


    def get_worker_params(self, config):
        """Parses worker parameters like job type and worker authorization key from endpoint config file.

        Args:
            config (dict): Config dictionary

        Returns:
            tuple (str, str): Tuple of job_type and worker_auth_key
        """
        worker_config = config.get('WORKER', {})
        job_type = worker_config.get('job_type')    
        if job_type == None:
            APIServer.logger.error("No job_type for worker configured!")
        else:
            APIServer.logger.info("Worker job type: " + job_type)
        worker_auth_key = worker_config.get('auth_key')
        return job_type, worker_auth_key   


    def get_ep_static_files(self, config):
        ep_static_files = config.get('HTML', {})
        for static_file in ep_static_files:
            entry = ep_static_files[static_file]
            APIServer.logger.info(" - " + static_file + " -> " + entry['file'])
        return ep_static_files


    def load_endpoint_configuration(self, config_file):
        APIServer.logger.info(f'Reading endpoint config: {config_file}')
        
        config = None
        with open(config_file, 'r') as f:
            config = toml.load(f)

        endpoint_description = self.get_endpoint_descriptions(config)

        APIServer.logger.debug(str(config))

        param_config = self.get_param_config(config)
        job_type, worker_auth_key = self.get_worker_params(config)
        ep_static_files = self.get_ep_static_files(config)

        APIServer.endpoints[endpoint_description[1]] = APIEndpoint(
            self, *endpoint_description, *param_config, job_type, worker_auth_key, ep_static_files
        )
        

    def load_endpoint_configurations(self, app):
        config_dir = APIServer.args.ep_config
        APIServer.logger.info('--- Searching endpoints configurations in {config_dir}')
        if pathlib.Path(config_dir).is_dir():
            for config_file in pathlib.Path(config_dir).glob('**/ml_api_endpoint.cfg'):
                self.load_endpoint_configuration(config_file)
        elif pathlib.Path(config_dir).is_file():
            self.load_endpoint_configuration(config_dir)
        elif ',' in config_dir:
            for config_file in config_dir.split(','):
                self.load_endpoint_configuration(config_file)
        else:
            APIServer.logger.error("!!! No Endpoint Configuration found, please specify where to load ml_api_endpoing.cfg with the --ep_config argument")


    async def validate_worker_queue(self, queue, req_json):
        job_type = req_json.get('job_type')
        if queue == None:
            if APIServer.args.dev:
                job_cmd = { 'cmd': "error", 'msg': f"No job queue for job_type: {job_type}" }
            else:
                job_cmd = { 'cmd': "warning", 'msg': f"No job queue for job_type: {job_type}" }

        elif queue.worker_auth_key != req_json.get('auth_key'):
            job_cmd = { 'cmd': "error", 'msg': f"Worker not authorized." }
        else: 
            job_cmd = {'cmd': 'ok'}
            if not req_json.get('status_check'):
                if req_json.get('auth') not in queue.registered_workers:
                    queue.registered_workers[req_json.get('auth')] = {
                        'status': 'waiting',
                        'jobs_done': 0,
                        'retry': False,
                        'last_request': time.time(),
                        'job_timeout': req_json.get('request_timeout', 60) * 0.9
                        }
                else:
                    worker = queue.registered_workers[req_json.get('auth')]
                    worker['status'] = 'waiting'
                    worker['last_request'] = time.time()
                    worker['job_timeout']: req_json.get('request_timeout', 60) * 0.9

        return job_cmd


    async def wait_for_valid_job(self, queue, req_json):
        job_id = None
        auth = req_json.get('auth')
        worker = queue.registered_workers.get(auth)
        got_valid_job = False
        if not worker.get('retry'):
            APIServer.logger.info(f"worker '{auth}' with {req_json.get('version')} waiting on '{req_json.get('job_type')}' queue for a job ... ")
        else:
            APIServer.logger.debug(f"worker '{auth}' with {req_json.get('version')} waiting on '{req_json.get('job_type')}' queue for a job ... ")
        
        while not got_valid_job:
            try:
                job_data = await queue.get(job_timeout=worker.get('job_timeout', 54))    # wait on queue for job
            except asyncio.TimeoutError:
                worker['retry'] = True
                return {'cmd': 'no_job'}
                
            queue.task_done()   # take it out of the queue
            worker['status'] = 'processing'
            
            client_session_auth_key = job_data.pop('client_session_auth_key', '')
            if not client_session_auth_key in self.registered_client_sessions:
                APIServer.logger.warn(f"discarding job, client session auth key not valid anymore")
            else:
                job_id = job_data['job_id']
                got_valid_job = (APIServer.job_states[job_id] == JobState.QUEUED)

        APIServer.job_states[job_id] = JobState.PROCESSING
        APIServer.logger.info(f"'{auth}' got job {job_id}")
        job_data['cmd'] = 'job'

        endpoint = APIServer.endpoints.get(job_data['endpoint_name'])
        job_data['progress_descriptions'] = endpoint.ep_progress_param_config
        job_data['output_descriptions'] = endpoint.ep_output_param_config
        job_data['start_time_compute'] = time.time()
        return job_data


    @staticmethod #stream=True in add_route() only works if staticmethod?
    async def stream_progress_to_client(request):
        client_session_auth_key = request.args.get('client_session_auth_key')
        job_id = request.args.get('job_id')
        if not client_session_auth_key:
            job_cmd = { 'cmd': "error", 'msg': f"client_session_auth_key missing" }
            return sanic_json(job_cmd)
        endpoint_name = APIServer.registered_client_sessions.get(client_session_auth_key)
        if not endpoint_name:
            job_cmd = { 'cmd': "error", 'msg': f"client_session_auth_key not authorized" }
            return sanic_json(job_cmd)
        if not job_id:
            job_cmd = { 'cmd': "error", 'msg': f"job_id missing" }
            return sanic_json(job_cmd)

        job_type = APIServer.endpoints.get(endpoint_name).worker_job_type
        queue = APIServer.job_queues.get(job_type)
        if not queue:
            job_cmd = { 'cmd': "error", 'msg': f"Internal Error: Queue not found" }
            return sanic_json(job_cmd)


        async def stream_sse(response):
            previous_progress_state = {}
            previous_queue_position = -1
            job_state = APIServer.job_states.get(job_id, JobState.UNKNOWN)
            while (job_state == JobState.QUEUED) or (job_state == JobState.PROCESSING):
                progress_state = APIServer.progress_states.get(job_id, previous_progress_state)
                if not progress_state:
                    progress_state['progress'] = 0                    
                progress_state['job_state'] = job_state.value

                queue_position = 0
                if job_state == JobState.QUEUED:
                    queue_position = queue.get_rank_for_job_id(job_id)

                if (queue_position != previous_queue_position) or (progress_state != previous_progress_state):
                    previous_progress_state = progress_state
                    previous_queue_position = queue_position
                    progress_state['queue_position'] = queue_position
                    await response.write(f'data: {json.dumps(progress_state)}\n\n')

                await asyncio.sleep(0.5)
                job_state = APIServer.job_states.get(job_id, JobState.UNKNOWN)        
                if job_state == JobState.PROCESSING:
                    job_future =  APIServer.job_result_futures.get(job_id, None)
                    if job_future and job_future.done():
                        endpoint = APIServer.endpoints.get(endpoint_name)
                        progress_state['job_result'] = await endpoint.finalize_request(request, job_id, job_future, {})
                        job_state = APIServer.job_states.get(job_id, job_state)                               
                        progress_state['job_state'] = job_state.value
                        progress_state['progress'] = 100                  
                        progress_state['queue_position'] = 0
                        await response.write(f'data: {json.dumps(progress_state)}\n\n')

        headers = {'Content-Type': 'text/event-stream'}
        return sanic_response.ResponseStream(stream_sse, headers=headers)


    @staticmethod
    def generate_auth_key():
        return str(uuid.uuid4())


    def init(self, args):
        
        self.__setup_worker_interface() # has to be done before app.run() is called
        self.register_listener(self.load_server_configuration, 'before_server_start') # maybe better without listener to have config in every main and worker process?
        self.register_listener(self.setup_static_routes, 'before_server_start')
        self.register_listener(self.load_endpoint_configurations, 'before_server_start')
        self.register_listener(self.create_job_queues, "after_server_start")


    def create_job_queues(self, app, loop):
        APIServer.logger.info("--- creating job queues")
        for endpoint in APIServer.endpoints.values():
            job_type = endpoint.worker_job_type
            if not job_type in APIServer.job_queues:
                APIServer.job_queues[job_type] = JobQueue(job_type, endpoint.worker_auth_key)
                APIServer.logger.info(f'Queue for job type: {job_type} initialized')


    def __setup_worker_interface(self):
        self.add_route(self.worker_job_request_json, "/worker_job_request", methods=["POST"])
        self.add_route(self.worker_job_result_json, "/worker_job_result", methods=["POST"])
        self.add_route(self.worker_job_progress, "/worker_job_progress", methods=["POST", "GET"])
        self.add_route(self.worker_check_server_status, "/worker_check_server_status", methods=["POST"])
        self.add_route(self.get_client_session_auth_key, "/get_client_session_auth_key", methods=["POST", "GET"])
        self.add_route(self.stream_progress_to_client ,"/stream_progress", methods=["POST", "GET"], stream=True)

   
    def setup_static_routes(self, app):
        APIServer.logger.info("--- setup static routes")
        config_file_path = os.path.dirname(APIServer.args.server_config)
        for slug in APIServer.static_routes:
            route = APIServer.static_routes[slug]
            route_type = route.get("type", "file")
            route_path = route.get("path", None)
            num = 0
            if not route_path:
                route_path = route.get("file", None)
            if route_path:
                if not os.path.isabs(route_path):
                    route_path = os.path.abspath(os.path.join(config_file_path, route_path))
            if route_type == "file":
                # add the static route
                self.static(slug, route_path, name="app_static" + str(num))
            elif route_type == "md":
                # do markdown processing
                APIServer.logger.info("MD")
                compiled_path = route.get("compiled_path")
                compiled_path = os.path.abspath(os.path.join(config_file_path, compiled_path))
                css_file = route.get("css_file")
                output_file = os.path.join(compiled_path, os.path.splitext(os.path.basename(route_path))[0] + ".html")
                APIServer.logger.info("OUTPUT: " + compiled_path)
                if not os.path.exists(compiled_path):
                    os.makedirs(compiled_path)
                MarkDownCompiler.compile(route_path, output_file, css_file)
                self.static(slug, output_file, name="app_static" + str(num))
                
            elif route_type == 'scss':
                # do scss processing
                APIServer.logger.info("SCSS")
                compiled_path = route.get("compiled_path")
                compiled_path = os.path.abspath(os.path.join(config_file_path, compiled_path))
                # compile SASS files
                manifest = SassManifest(slug, compiled_path, route_path, css_type='scss')
                manifest.compile_webapp(self, register_static=True)
            num += 1
            APIServer.logger.info("Static: " + slug + " -> [" + route_type + "] " + str(route_path))


    def configure_logger(self):

        file_handler = logging.FileHandler(filename='api_server/log_api_server.log')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        self.set_logger_level(APIServer.logger)
        APIServer.logger.addHandler(file_handler)

        if not APIServer.args.hide_logging:         
            stream_handler = logging.StreamHandler()
            self.set_logger_level(stream_handler)
            stream_handler.setFormatter(formatter)
            APIServer.logger.addHandler(stream_handler)

        sanic_loggers = ('sanic.access', 'sanic.root', 'sanic.error')
        
        for logger_name in sanic_loggers:
            logger = logging.getLogger(logger_name)
            self.set_logger_level(logger)
            if not APIServer.args.hide_logging:
                logger.addHandler(stream_handler)

        APIServer.logger.debug("Command line arguments:\n" + str(APIServer.args))  

    def set_logger_level(self, logger):
        logger.setLevel(logging.DEBUG) if APIServer.args.dev else logger.setLevel(logging.INFO)




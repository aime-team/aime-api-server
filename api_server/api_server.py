# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from sanic import Sanic
from sanic import response as sanic_response

from sanic.response import json as sanic_json
from sanic.log import logging


from http import HTTPStatus
import os
import time
from pathlib import Path
import toml
import urllib.request
import json
import asyncio

from .api_endpoint import APIEndpoint
from .job_queue import JobQueue, JobState
from .flags import Flags
from .utils import StaticRouteHandler, shorten_strings
from .__version import __version__


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
    input_type_config = {}
    default_authentification = "None"
    default_authorization = "None"
    default_authorization_keys = {}
    logger = logging.getLogger('API')
    host = None
    port = None

    def __init__(self, api_name):
        """Constructor

        Args:
            api_name (str): Name of API server
            args (argparse.Namespace): Command line arguments parsed with argparse
        """
        flags = Flags()
        APIServer.args = flags.args
        APIServer.host, APIServer.port = APIServer.get_host_and_port()
        self.configure_logger()
        super().__init__(api_name, configure_logging=not APIServer.args.no_sanic_logger)      
        self.init(APIServer.args)


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
                    'cmd': 'job',
                    'endpoint_name': 'stable_diffusion_xl_txt2img',
                    'wait_for_result': False,
                    'job_data': {
                        'job_id': 'JID1', 
                        'start_time': 1700424731.952994, 
                        'start_time_compute': 1700424731.9582381
                        'prompt': 'prompt',
                    },
                    'progress_descriptions': = {
                        'progress_images': {
                            'type': 'image_list',
                            'format': 'JPEG',
                            'color_space': 'RGB'
                        }
                    }
                    'output_descriptions': = {
                        'images': {
                            'type': 'image_list',
                            'format': 'JPEG',
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
        APIServer.logger.debug(f'Request on /worker_job_request: {shorten_strings(req_json)}')
        queue = APIServer.job_queues.get(req_json.get('job_type'))
        job_cmd = await self.validate_worker_queue(queue, req_json)
        if job_cmd['cmd'] not in ('ok', 'warning'):
            APIServer.logger.warning(f"Worker {req_json.get('auth')} tried a job request for job type {req_json.get('job_type')}, but following error occured: {job_cmd.get('msg')}")
            return sanic_json(job_cmd)
             
        job_cmd = await self.wait_for_valid_job(queue, req_json)
        return sanic_json(job_cmd)


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
        job_cmd = await self.validate_worker_queue(APIServer.job_queues.get(result.get('job_type')), result)
        if job_cmd['cmd'] not in ('ok', 'warning'):
            APIServer.logger.warning(f"Worker {result.get('auth')} tried to send job result for job type {result.get('job_type')}, but following error occured: {job_cmd.get('msg')}")
            return sanic_json(job_cmd)
        job_id = result.get('job_id')

        try:
            APIServer.job_result_futures[job_id].set_result(result)
            response = {'cmd': 'ok'}
        except KeyError:
            job_id = 'unknown job'
            response = {'cmd': 'warning', 'msg': f"Job {job_id} invalid! Couldn't process job results!"}
        APIServer.logger.info(f"Worker '{result.get('auth')}' processed job {job_id}")
        return sanic_json(response)

    
    def process_job_result(self, request):
        req_json = request.json
        APIServer.logger.debug(f'Request on /worker_job_result: {shorten_strings(req_json)}')
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

                request.json = [{    
                    'job_id': 'JID1',
                    'progress': 50,
                    'progress_data': {'progress_images': ['base64-string', 'base64-string', ...]},
                    'start_time_compute': 1700424731.9582381,
                    'start_time': 1700424731.952994
                }]
        """
        req_json = request.json
        APIServer.logger.debug(f'Request on /worker_job_progress: {shorten_strings(req_json)}')
        if not isinstance(req_json, list): # compatibility fix: api_worker_interface < version 0.70
            req_json = [req_json]
        job_cmd_list = list()
        for job_data in req_json:
            job_id = job_data.get('job_id')
            job_type = job_data.get('job_type')
            job_cmd = await self.validate_worker_queue(APIServer.job_queues.get(job_type), job_data)
            if job_cmd.get('cmd') not in ('ok', 'warning'):
                APIServer.logger.warning(f"Worker {job_data.get('auth')} tried to send progress for job {job_id} with job type {job_type}, but following error occured: {job_cmd.get('msg')}")
                return sanic_json(job_cmd) # Fast exit if worker is not authorized or wrong job type.

            if APIServer.job_result_futures.get(job_id):

                APIServer.progress_states[job_id] = job_data
            else:
                job_cmd = {'cmd': 'warning', 'msg': f'Job with job id {job_id} not valid'}
                APIServer.logger.warning(f"Worker {job_data.get('auth')} tried to send progress for job {job_id} with job type {job_type}, but following error occured: {job_cmd.get('msg')}")
            job_cmd_list.append(job_cmd)
       
        return sanic_json(job_cmd_list)



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
            result = { 'cmd': "warning", 'msg': 'API Server still initializing'}
        return sanic_json(result)


    def load_server_configuration(self, app):
        """Parses server configuration file.
        """
        config_file = APIServer.args.server_config
        APIServer.logger.info("Reading server config: " + str(config_file))

        with open(config_file, "r") as f:
            server_config = toml.load(f)
        self.set_server_clients_config(server_config)
        self.set_server_sanic_config(server_config, app)
        if not self.args.ep_config:
            self.args.ep_config = server_config.get('SERVER').get('endpoint_configs', './endpoints')
        APIServer.input_type_config = server_config.get('INPUTS', {})
        APIServer.static_routes = server_config.get('STATIC', {})


    def set_server_clients_config(self, server_config):
        server_clients_config = server_config.get('CLIENTS', {})
        APIServer.default_authentication = server_clients_config.get("default_authentication", "User")
        APIServer.default_authorization = server_clients_config.get("default_authorization", "Key")
        APIServer.default_authorization_keys = server_clients_config.get("default_authorization_keys", {})
        APIServer.default_client_request_limit = server_clients_config.get("default_client_request_limit", 0)
        APIServer.default_provide_worker_meta_data = server_clients_config.get("default_provide_worker_meta_data", False)


    def init_endpoint(self, config_file):
        with open(config_file, 'r') as file:
            config = toml.load(file)
            name = config.get('ENDPOINT', {}).get('name')
        APIServer.endpoints[name] = APIEndpoint(self, config_file)

    def init_all_endpoints(self, app, loop):

        config_dir = APIServer.args.ep_config
        APIServer.logger.info(f'--- Searching endpoints configurations in {config_dir}')
        if Path(config_dir).is_dir():
            for config_file in Path(config_dir).glob('**/aime_api_endpoint.cfg'):
                self.init_endpoint(config_file)
        elif Path(config_dir).is_file():
            self.init_endpoint(config_dir)
        elif ',' in config_dir:
            for config_file in config_dir.split(','):
                self.init_endpoint(config_file)
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
            job_cmd = { 'cmd': "error", 'msg': f"Worker not authorized!" }
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
                    worker['last_request'] = time.time()
                    worker['job_timeout'] = req_json.get('request_timeout', 60) * 0.9
                    if req_json.get('progress'):
                        worker['status'] = f"processing job {req_json.get('job_id')}"
                    else:
                        worker['status'] = 'waiting'

        return job_cmd


    async def wait_for_valid_job(self, queue, req_json):
        job_id = None
        auth = req_json.get('auth')
        worker = queue.registered_workers.get(auth)
        got_valid_job = False
        logger_string = f"Worker '{auth}' in version {req_json.get('worker_version')} with {req_json.get('version')} waiting on '{req_json.get('job_type')}' queue for a job ... "
        if not worker.get('retry'):
            APIServer.logger.info(logger_string)
        else:
            APIServer.logger.debug(logger_string)
            worker['retry'] = False
        
        job_timeout = worker.get('job_timeout', 54)
        max_job_batch = req_json.get('max_job_batch', 1)

        while not got_valid_job:
            try:
                job_data = await queue.get(job_timeout=job_timeout)    # wait on queue for job
            except asyncio.TimeoutError:
                worker['retry'] = True
                return {'cmd': 'no_job', 'api_server_version': __version__}
                
            queue.task_done()   # take it out of the queue
            worker['status'] = 'processing'
            
            client_session_auth_key = job_data.pop('client_session_auth_key', '')
            if not client_session_auth_key in self.registered_client_sessions:
                APIServer.logger.warn(f"discarding job, client session auth key not valid anymore")
            else:
                job_id = job_data['job_id']
                got_valid_job = (APIServer.job_states[job_id] == JobState.QUEUED)

        endpoint_name = job_data.pop('endpoint_name', '')
        APIServer.job_states[job_id] = JobState.PROCESSING
        APIServer.logger.info(f"Worker '{auth}' got job {job_id}")
        job_data['start_time_compute'] = time.time()

        job_batch_data = [job_data]

        # fill batch with already waiting jobs
        if(max_job_batch > 1):
            fetch_waiting_jobs = True
            while((len(job_batch_data) < max_job_batch) and fetch_waiting_jobs):
                job_data = queue.fetch_waiting_job()
                if(job_data):
                    client_session_auth_key = job_data.pop('client_session_auth_key', '')
                    if not client_session_auth_key in self.registered_client_sessions:
                        APIServer.logger.warn(f"discarding job, client session auth key not valid anymore")
                    else:
                        job_id = job_data['job_id']
                        if(APIServer.job_states[job_id] == JobState.QUEUED):
                            APIServer.job_states[job_id] = JobState.PROCESSING
                            job_data.pop('endpoint_name', '')
                            APIServer.logger.info(f"Worker '{auth}' got job {job_id}")
                            job_data['start_time_compute'] = time.time()
                            job_batch_data.append(job_data)
                else:
                    fetch_waiting_jobs = False

        job_cmd = { 'cmd': 'job', 'api_server_version': __version__ }
        endpoint = APIServer.endpoints.get(endpoint_name)
        job_cmd['endpoint_name'] = endpoint_name
        job_cmd['progress_output_descriptions'] = endpoint.ep_progress_param_config.get('OUTPUTS')
        job_cmd['final_output_descriptions'] = endpoint.ep_output_param_config
        job_cmd['job_data'] = job_batch_data
        return job_cmd


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


    def init(self, args):
        
        self.__setup_worker_interface() # has to be done before app.run() is called
        self.register_listener(self.load_server_configuration, 'before_server_start') # maybe better without listener to have config in every main and worker process?
        self.register_listener(self.setup_static_routes, 'before_server_start')
        self.register_listener(self.init_all_endpoints, 'before_server_start')
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
        self.add_route(self.stream_progress_to_client ,"/stream_progress", methods=["POST", "GET"], stream=True)


    def setup_static_routes(self, app):
        app.logger.info("--- setup static routes")
        static_route_handler = StaticRouteHandler(Path(app.args.server_config).parent, app)
        static_route_handler.setup_static_routes(app.static_routes)


    def set_server_sanic_config(self, server_config, app):
        config = server_config.get('SANIC', {})
        app.update_config({key.upper(): value for key, value in config.items()})


    @staticmethod
    def get_host_and_port():
        with open(APIServer.args.server_config, "r") as file:
            server_config = toml.load(file).get('SERVER')
            
            if APIServer.args.host:
                host = APIServer.args.host
            else:
                host = server_config.get('host')
            if APIServer.args.port:
                port = APIServer.args.port
            else:            
                port = server_config.get('port')
        return host, port


    def configure_logger(self):

        file_handler = logging.FileHandler(filename='api_server/log_api_server.log', mode='w')
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
            self.set_logger_level(logger)  # Bugged logger sanic.access: "INFO" messages only appear in "DEBUG" (args.dev = True) mode
            # But since these INFO messages are redundant and spamming the terminal, thats the desired behaviour
            logger.addHandler(file_handler) # not working for sanic loggers
            if not APIServer.args.hide_logging:
                logger.addHandler(stream_handler)


    def set_logger_level(self, logger):
        logger.setLevel(logging.DEBUG) if APIServer.args.dev else logger.setLevel(logging.INFO)


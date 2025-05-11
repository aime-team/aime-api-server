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
from .job_queue import JobState, JobHandler
from .openai import OpenAI
from .flags import Flags
from .utils.misc import StaticRouteHandler, shorten_strings, CustomFormatter
from .utils.ffmpeg import FFmpeg


logging.getLogger('asyncio').setLevel(logging.ERROR)
        




class APIServer(Sanic):
    """AIME API Server

    Args:
        api_name (str): Name of API server
    """
    endpoints = {}  # key: endpoint_name
    job_handler = None
    registered_keys = dict() # client_session_auth_key: api_key
    args = None
    static_routes = {}
    worker_config = {}
    input_param_config = {}
    openai_config = {}
    logger = logging.getLogger('API')
    host = None
    port = None
    admin_backend = None
    openai = None

    def __init__(self, api_name):
        """Constructor

        Args:
            api_name (str): Name of API server
        """
        flags = Flags()
        APIServer.args = flags.args
        APIServer.host, APIServer.port = APIServer.get_host_and_port()
        self.configure_logger()
        super().__init__(api_name, configure_logging=False)
        self.init(APIServer.args)


    @classmethod
    def connect_admin_backend(cls, admin_backend):
        cls.admin_backend = admin_backend


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
        response_cmd = APIServer.job_handler.validate_worker_request(req_json)
        if response_cmd.get('cmd') != 'ok':
            APIServer.logger.warning(
                f"Worker {req_json.get('auth')} tried a job request for job type {req_json.get('job_type')}, "
                f"but following error occured: {response_cmd.get('msg')}"
            )
            return sanic_json(response_cmd)
             
        response_cmd = await APIServer.job_handler.worker_job_request(req_json)
        return sanic_json(response_cmd)


    async def worker_job_result_json(self, request):
        """Receive final job result from API worker interface via route /worker_job_result.
        Processes the result and puts it to the future related to the job initialized in APIEndpoint.api_request
        to make it available by APIEndpoint.api_request and APIEndpoint.api_progress to send it to the client.

        Args:
            request (sanic.request.types.Request): API worker interface request containing the job results.

        Returns:
            sanic.response.types.JSONResponse: Response to API worker interface with 'cmd': 'ok' when API server received data.
        """
        req_json = request.json
        response_cmd = APIServer.job_handler.validate_worker_request(req_json)
        if response_cmd.get('cmd') != 'ok':
            APIServer.logger.warning(
                f"Worker {req_json.get('auth')} tried to send job result for job {progress_result.get('job_id')} "
                f"with job type {req_json.get('job_type')}, but following error occured: {response_cmd.get('msg')}"
            )
            return sanic_json(response_cmd)
        response_cmd = await APIServer.job_handler.worker_set_job_result(req_json)
        return sanic_json(response_cmd)
    

    async def worker_job_progress(self, request):
        """Receive progress results from api worker interface via route /worker_job_progress 
        and put it to APIServer.job_handler.progress_states[job_id] to make it available for APIEndpoint.api_progress(). 

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
        response_cmd_list = list()
        for progress_result in req_json:
            response_cmd = APIServer.job_handler.validate_worker_request(progress_result)
            if response_cmd.get('cmd') not in ('ok'):
                APIServer.logger.warning(
                    f"Worker {progress_result.get('auth')} tried to send progress for job {progress_result.get('job_id')} "
                    f"with job type {progress_result.get('job_type')}, but following error occured: {response_cmd.get('msg')}"
                )
                return sanic_json(response_cmd) # Fast exit if worker is not authorized or wrong job type.
            response_cmd = await APIServer.job_handler.worker_update_progress_state(progress_result)
            response_cmd_list.append(response_cmd)
       
        return sanic_json(response_cmd_list)



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

        if APIServer.job_handler and APIServer.job_handler.job_types and req_json:
            result = APIServer.job_handler.validate_worker_request(req_json)
        else:
            result = { 'cmd': "warning", 'msg': 'API Server still initializing'}
        return sanic_json(result)


    async def validate_key(self, request):
        """Route /api/validate_key to check if api key is valid

        Args:
            request (sanic.request.types.Request): Client request containing api key "key"

        Returns:
            sanic.response.types.JSONResponse: Response to client. Example: {'success': True, 'error': None}
        """        
        api_key = request.args.get('key', None)
        if self.admin_backend:
            response = await self.admin_backend.admin_is_api_key_valid(api_key)
            return sanic_json(
                {
                    'success': response.get('valid'),
                    'error': response.get('error_msg')
                }
            )
        else:
            return sanic_json(
                {
                    'success': False,
                    'error': 'No Admin Backend to validate api key'
                }
            )

    async def get_endpoints(self, request):
        """Route /api/endpoints to retrieve a list of all endpoints. If request contains api_key only authorized endpoints are listed.

        Args:
            request (sanic.request.types.Request): Client request

        Returns:
            sanic.response.types.JSONResponse: Response to client. Example: {'endpoints': ['endpoint_name_1, endpoint_name_2, ...]}  
        """
        api_key = request.args.get('key')
        endpoints = list(self.endpoints.keys())
        if api_key:
            response = await self.admin_backend.admin_is_api_key_valid(api_key)
            if not response.get('valid'):
                return sanic_json(
                    {
                        'error': response.get('error_msg')
                    },
                    status = 401
                )
            endpoints = [
                endpoint_name for endpoint_name in endpoints if await self.admin_backend.admin_is_api_key_authorized_for_endpoint(api_key,endpoint_name)
            ]
        return sanic_json(
            {
                'endpoints': endpoints
            }
        )


    def load_server_configuration(self, app):
        """Parses server configuration file.
        """
        config_file = APIServer.args.server_config
        APIServer.logger.info("Reading server config: " + str(config_file))

        with open(config_file, "r") as f:
            APIServer.server_config = toml.load(f)
          
        self.set_server_sanic_config(APIServer.server_config, app)
        if not self.args.ep_config:
            self.args.ep_config = APIServer.server_config.get('SERVER').get('endpoint_configs', './endpoints')
        APIServer.input_param_config = APIServer.server_config.get('INPUTS', {})
        APIServer.static_routes = APIServer.server_config.get('STATIC', {})
        APIServer.worker_config = APIServer.server_config.get('WORKERS', {})
        APIServer.openai_config = APIServer.server_config.get('OPENAI', {})


    def init_endpoint(self, config_file):
        with open(config_file, 'r') as file:
            config = toml.load(file)
            name = config.get('ENDPOINT', {}).get('name')
            job_type = config.get('WORKER', {}).get('job_type')
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


    def init_job_handler(self, app, loop):
        APIServer.job_handler = JobHandler(app)


    def init_openai(self, app, loop):
        OpenAI(self)


    @staticmethod #stream=True in add_route() only works if staticmethod?
    async def stream_progress_to_client(request):
        client_session_auth_key = request.args.get('client_session_auth_key')
        job_id = request.args.get('job_id')
        if not client_session_auth_key:
            job_cmd = { 'cmd': "error", 'msg': f"client_session_auth_key missing" }
            return sanic_json(job_cmd)
        endpoint_name = APIServer.registered_keys.get(client_session_auth_key)
        if not endpoint_name:
            job_cmd = { 'cmd': "error", 'msg': f"client_session_auth_key not authorized" }
            return sanic_json(job_cmd)
        if not job_id:
            job_cmd = { 'cmd': "error", 'msg': f"job_id missing" }
            return sanic_json(job_cmd)

        job_type = APIServer.endpoints.get(endpoint_name).worker_job_type
        queue = APIServer.job_handler.job_queues.get(job_type)
        if not queue:
            job_cmd = { 'cmd': "error", 'msg': f"Internal Error: Queue not found" }
            return sanic_json(job_cmd)


        async def stream_sse(response):
            previous_progress_state = {}
            previous_queue_position = -1
            job_state = APIServer.job_handler.get_job_state(job_id)
            while (job_state == JobState.QUEUED) or (job_state == JobState.PROCESSING):
                progress_state = APIServer.job_handler.progress_states.get(job_id, previous_progress_state)
                if not progress_state:
                    progress_state['progress'] = 0                    
                progress_state['job_state'] = job_state

                queue_position = 0
                if job_state == JobState.QUEUED:
                    queue_position = queue.get_rank_for_job_id(job_id)

                if (queue_position != previous_queue_position) or (progress_state != previous_progress_state):
                    previous_progress_state = progress_state
                    previous_queue_position = queue_position
                    progress_state['queue_position'] = queue_position
                    await response.write(f'data: {json.dumps(progress_state)}\n\n')

                await asyncio.sleep(0.5)
                job_state = APIServer.job_handler.get_job_state(job_id)
                if job_state == JobState.PROCESSING:
                    if APIServer.job_handler.is_job_future_done(job_id):
                        endpoint = APIServer.endpoints.get(endpoint_name)
                        progress_state['job_result'] = await endpoint.finalize_request(request, job_id)
                        job_state = APIServer.job_handler.get_job_state(job_id)
                        progress_state['job_state'] = job_state
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
        self.register_listener(self.init_openai, 'before_server_start')
        self.register_listener(self.init_job_handler, 'after_server_start')
        self.register_listener(FFmpeg.is_ffmpeg_installed, 'after_server_start')
        self.register_listener(self.start_job_clean_up_background_task, 'after_server_start')


    def __setup_worker_interface(self):
        self.add_route(self.worker_job_request_json, "/worker_job_request", methods=["POST"])
        self.add_route(self.worker_job_result_json, "/worker_job_result", methods=["POST"])
        self.add_route(self.worker_job_progress, "/worker_job_progress", methods=["POST", "GET"])
        self.add_route(self.worker_check_server_status, "/worker_check_server_status", methods=["POST"])
        self.add_route(self.stream_progress_to_client ,"/stream_progress", methods=["POST", "GET"], stream=True)
        self.add_route(self.validate_key, "/api/validate_key", methods=["POST", "GET"], name='api$validate_key')
        self.add_route(self.get_endpoints, "/api/endpoints", methods=["POST", "GET"], name='api$get_endpoints')


    def setup_static_routes(self, app):
        app.logger.info("--- setup static routes")
        static_route_handler = StaticRouteHandler(Path(app.args.server_config).parent, app)
        static_route_handler.setup_static_routes(app.static_routes)


    def set_server_sanic_config(self, server_config, app):
        config = server_config.get('SANIC', {})
        app.update_config({key.upper(): value for key, value in config.items()})


    async def start_job_clean_up_background_task(self, app, loop):
        loop.create_task(self.periodically_clean_up_jobs())


    async def periodically_clean_up_jobs(self, update_interval=5):
        while True:
            await self.job_handler.clean_up_jobs()
            await asyncio.sleep(update_interval)


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
        
        formatter = CustomFormatter(self.args.no_colour)
        file_handler.setFormatter(formatter)
        self.set_logger_level(APIServer.logger)
        APIServer.logger.addHandler(file_handler)

        if not APIServer.args.hide_logging:         
            stream_handler = logging.StreamHandler()
            self.set_logger_level(stream_handler)
            stream_handler.setFormatter(formatter)
            APIServer.logger.addHandler(stream_handler)

        sanic_loggers = ('sanic.access', 'sanic.root', 'sanic.error') # sanic.access is disabled by default, but can be enabled by setting access_log = true in aime_api_server.cfg 
        sanic_formatter = CustomFormatter(True)
        sanic_file_handler = logging.FileHandler(filename='api_server/log_api_server.log', mode='w')
        sanic_file_handler.setFormatter(sanic_formatter)
        sanic_stream_handler = logging.StreamHandler()
        sanic_stream_handler.setFormatter(sanic_formatter)
        for logger_name in sanic_loggers:
            logger = logging.getLogger(logger_name)
            self.set_logger_level(logger) 
            logger.addHandler(sanic_file_handler)
            if not APIServer.args.hide_logging:
                logger.addHandler(sanic_stream_handler)


    def set_logger_level(self, logger):
        logger.setLevel(logging.DEBUG) if APIServer.args.dev else logger.setLevel(logging.INFO)


from .__version import __version__
from .utils.misc import get_job_counter_id, shorten_strings

class AdminInterface():
    """
    AIME API Server AdminInterface provided by API Server

    Args:
        app (Sanic): Instance of Sanic server
        args: command line arguments that where passed
        server_configuration: JSON of loaded server configuration

    Conventions:
        - only class admin backend imports
        - communication with API server only through this interface!
        - no python objects: only strings, int, boolean, float and dict and arrays will be passed
        - is_ do_ methods are calls from API Server -> Admim BE
    """
    def __init__(self, app, args, server_configuration):
        # overwritten and implemented by Admin BE
        self.app = app


    # API key authorization
    # 
    async def admin_is_api_key_authorized_for_endpoint(self, api_key, endpoint_name):
        # implemented by Admin BE        
        return False


    # API Key Validation
    async def admin_is_api_key_valid(self, api_key:str, ip_address:str):
        # implemented by Admin BE
        return {
            'valid': True,
            'error_msg': None
            }



    async def api_get_endpoint_list(self):
        """Retrieve all endpoints known to the API Server.

        Returns:
            list[str]: List of known endpoints
        """
        return [endpoint_name for endpoint_name in self.app.endpoints.keys()]



    async def api_get_endpoint_status(self, endpoint_name):
        """Retrieve 

        Args:
            endpoint_name (str): Name of the endpoint

        Returns:
            dict: Dictionary with endpoint status
        """        
        endpoint = self.app.endpoints.get(endpoint_name)
        if endpoint:
            return await endpoint.status_data
            # Implemented by API Server
            ## return dictonary with:
            # enable / disable
            # num current workers
            # last request time
            # current request in queue
            # current processing requests
            # average processing time
            # num request since startup
            # num mailformed requests
            # num unauthorized requests
            # num process requests finished
            # num process requests with error
            # num process requests aborted



    async def api_add_endpoint(self, endpoint_name):
        # Implemented by API Server (later)
        pass


    async def api_delete_endpoint(self, endpoint_name):
        # Implemented by API Server (later)
        pass


    async def api_set_endpoint_enabled(self, endpoint_name):
        """Enable endpoint with given endpoint name

        Args:
            endpoint_name (str): Name of the endpoint

        Returns:
            bool: True if endpoint_name is present, False otherwise
        """        
        endpoint = self.app.endpoints.get(endpoint_name)
        if endpoint:
            endpoint.enable()
            return True
        else:
            return False

    async def api_set_endpoint_disabled(self, endpoint_name):
        """Disable endpoint with given endpoint name

        Args:
            endpoint_name (str): Name of the endpoint

        Returns:
            bool: True if endpoint_name is present, False otherwise
        """    
        endpoint = self.app.endpoints.get(endpoint_name)
        if endpoint:
            endpoint.disable()
            return True
        else:
            return False

    async def api_get_endpoint_config(self, endpoint_name):
        """Retrieve endpoint configuration of given endpoint name

        Args:
            endpoint_name (str): Name of the endpoint

        Returns:
            dict: Endpoint configuration
        """        
        endpoint = self.app.endpoints.get(endpoint_name)
        if endpoint:
            return endpoint.config


    async def api_set_endpoint_config(self, endpoint_name, config):
        # Implemented by API Server (later)
        pass


    # request statistics
    #
    async def admin_log_request_start(
        self,
        job_id,
        api_key,
        endpoint_name,
        start_time_utc,
        ip_address=None, 
        http_request_header:dict=None
        ):
        # Implemented by Admin BE
        pass


    async def admin_log_request_start_processing(self, job_id, start_time_compute_utc):
        # Implemented by Admin BE
        pass


    async def admin_log_request_end(
        self,
        job_id,
        start_time_compute_utc,
        end_time_utc,
        request_state, # 'success', 'failed', 'canceled' ,
        metrics=None, # dict
        request_error_msg=None
        ):
        # Implemented by Admin BE
        pass


    async def api_get_worker_list(self):
        """Retrieve list of all worker names.

        Returns:
            list[str]: List of workers
        """
        return [worker.auth for worker in await self.app.job_handler.get_all_workers()]


    async def api_get_worker_config(self, worker_name):
        """Retrieve configuration of worker with given worker name.

        Args:
            worker_name (str): Name of the worker

        Returns:
            dict: Worker configuration containing job_type, worker_auth_key, etc.
        """        
        return self.app.job_handler.get_worker_config(worker_name)

    async def api_get_worker_model(self, worker_name):
        """Retrieve the served model of the worker with given worker name.

        Args:
            worker_name (str): Name of the worker

        Returns:
            dict: Model configuration containing e.g. label, size, quantization, type, family and repo_name
        """
        return vars(self.app.job_handler.get_worker_model(worker_name))



    async def api_get_worker_status(self, worker_name):
        """Retrieve the current status of the worker with given worker name.

        Args:
            worker_name (str): Name of the worker

        Returns:
            str: Current worker status: 'processing', 'waiting', 'offline' or 'disabled'
        """        
        status = await self.app.job_handler.get_worker_state(worker_name)
        if status:
            return status.value


    async def admin_set_worker_enabled(self, worker_name):
        """Enable worker with given worker name

        Args:
            worker_name (str): Name of the worker

        Returns:
            bool: True if worker_name is present, False otherwise
        """        
        return await self.app.job_handler.enable_worker(worker_name)


    async def admin_set_worker_disabled(self, worker_name):
        """Disable worker with given worker name

        Args:
            worker_name (str): Name of the worker

        Returns:
            bool: True if worker_name is present, False otherwise
        """            
        return await self.app.job_handler.disable_worker(worker_name)



class MinimumAdminBackendImplementation(AdminInterface):



    async def admin_is_api_key_authorized_for_endpoint(self, api_key, endpoint_name):
        endpoint_config = await self.api_get_endpoint_config(endpoint_name)
        return True if api_key in endpoint_config.get('CLIENTS', {}).get('authorization_keys').values() else False
    

    # API Key Management
    async def admin_is_api_key_valid(self, api_key, ip_address):
        for endpoint_name in await self.api_get_endpoint_list():
            if await self.admin_is_api_key_authorized_for_endpoint(api_key, endpoint_name):
                return {
                    'valid': True,
                    'error_msg': None
                }
        return {
            'valid': False,
            'error_msg': 'Key not valid'
        }


    async def admin_log_request_start(
        self,
        job_id:str,
        api_key:str,
        endpoint_name:str,
        start_time_utc:float,
        ip_address:str=None,
        http_request_header:dict=None
        ):
        self.app.logger.debug(
            f'Admin Backend call to admin_log_request_start from '
            f'job: {get_job_counter_id(job_id)}, '
            f'key: {api_key}, '
            f'endpoint_name: {endpoint_name}, '
            f'ip_address: {ip_address}, '
            f'header: {http_request_header}'
            )


    async def admin_log_request_start_processing(self, job_id, start_time_compute_utc):
        self.app.logger.debug(
            f'Admin Backend call to admin_log_request_start_processing from job: {get_job_counter_id(job_id)}'
        )


    async def admin_log_request_end(
        self,
        job_id,
        start_time_compute_utc,
        end_time_utc,
        request_state, # 'success', 'failed', 'canceled'
        metrics=None, # dict
        request_error_msg=None
        ):
        self.app.logger.debug(
            f'Admin Backend call to admin_log_request_end from '
            f'job: {get_job_counter_id(job_id)}, '
            f'start_time_compute: {start_time_compute_utc}, '
            f'end_datetime: {end_time_utc}, '
            f'request_state: {request_state}, '
            f'metrics: {metrics}, '
            f'request_error_msg: {request_error_msg}'
        )

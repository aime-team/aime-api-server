from .__version import __version__


class AdminInterface():
    """
    AIME API Server AdminInterface provided by API Server

    Args:
        sanic (Sanic): Instance of Sanic server
        args: command line arguments that where passed
        server_configuration: JSON of loaded server configuration

    Conventions:
        - only class admin backend imports
        - communication with API server only through this interface!
        - no python objects: only strings, int, boolean, float and dict and arrays will be passed
        - is_ do_ methods are calls from API Server -> Admim BE
    """
    def __init__(self, sanic, args, server_configuration):
        # overwritten and implemented by Admin BE
        self.sanic = sanic


    #### user authentification / authorization
    # 
    async def admin_is_user_known(self, user_name):
        # implemented by Admin BE
        pass

    async def admin_do_log_in_user(self, user_name, password_hash):
        # implemented by Admin BE
        return False

    async def admin_do_log_out_user(self, user_name):
        # implemented by Admin BE
        return True

    async def admin_is_user_authorized_for_basic_operations(self, user_name, auth_key):
        # implemented by Admin BE        
        return False

    async def admin_is_user_authorized_for_endpoint(self, user_name, endpoint_name, auth_key):
        # implemented by Admin BE        
        return False


    # API Key Managment
    async def admin_is_api_key_valid(self, user_name, api_key, endpoint):
        # implemented by Admin BE
        return False


    async def api_get_endpoint_list(self):
        """Retrieve all endpoints known to the API Server.

        Returns:
            list of strings: List of known endpoints
        """
        return [endpoint_name for endpoint_name in self.sanic.endpoints.keys()]


    async def api_endpoint_status(self, endpoint_name):
        """_summary_

        Args:
            endpoint_name (_type_): _description_

        Returns:
            dict: Dictionary with endpoint status
        """        

        endpoint = self.sanic.endpoints.get(endpoint_name)
        job_type = self.sanic.job_type_interface.job_types.get(endpoint.worker_job_type)
        if job_type and endpoint:
            ep_status = endpoint.status_data
            ep_status.update({
                'num_workers_online': await job_type.get_num_workers_online(),
                'num_processing_requests': job_type.get_num_running_jobs(endpoint_name),
                'num_pending_requests': len(job_type.queue),
                'mean_request_duration': job_type.mean_duration,
                'num_free_slots': job_type.free_slots,
                'version': __version__

            })
            return ep_status
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


    async def api_set_endpoint_enable(self, endpoint_name):
        # Implemented by API Server
        pass


    async def api_get_endpoint_config(self, endpoint_name):
        endpoint = self.sanic.endpoints.get(endpoint_name)
        if endpoint:
            return endpoint.config


    async def api_set_endpoint_config(self, endpoint_name, config):
        # Implemented by API Server (later)
        pass


    # request statistics
    #
    async def admin_log_request_start(self, endpoint_name, user, job_id):
        # Implemented by Admin BE
        pass


    async def admin_log_request_processing(self, endpoint_name, user, job_id):
        # Implemented by Admin BE
        pass


    async def admin_log_request_end(self, endpoint_name, user, job_id, request_status):
        # Implemented by Admin BE
        # request_status: "error", "success"
        pass


    async def api_get_worker_list(self):
        return await self.sanic.job_type_interface.get_all_workers()


    async def api_get_active_worker_list(self):
        return await self.sanic.job_type_interface.get_all_active_workers()


    async def api_get_worker_status(self, worker_auth):
        status = await self.sanic.job_type_interface.get_worker_state(worker_auth)
        if status:
            return status.value


    async def admin_set_worker_online(self, worker_auth):
        return await self.sanic.job_type_interface.activate_worker(worker_auth)


    async def admin_set_worker_offline(self, worker_auth):
        return await self.sanic.job_type_interface.deactivate_worker(worker_auth)
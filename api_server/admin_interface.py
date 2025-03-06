
from .__version import __version__

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


    # user authentification / authorization
    # 
    async def admin_is_user_authenticated(self, request):
        # implemented by Admin BE
        pass

    async def admin_do_log_in_user(self, request):       # ---> request obj. should have json (email, password)
        # implemented by Admin BE
        return False

    async def admin_do_log_out_user(self, request):
        # implemented by Admin BE
        return True

    async def admin_is_user_authorized_for_basic_operations(self, user_email, auth_key):
        # implemented by Admin BE        
        return False

    async def admin_is_user_authorized_for_endpoint(self, user_email, endpoint_name, auth_key):
        # implemented by Admin BE        
        return False


    # API Key Managment
    async def admin_is_api_key_valid(self, user_email, api_key, endpoint):
        # implemented by Admin BE
        return False


    async def api_get_endpoint_list(self):
        """Retrieve all endpoints known to the API Server.

        Returns:
            list of strings: List of known endpoints
        """
        return [endpoint_name for endpoint_name in self.app.endpoints.keys()]



    async def api_get_endpoint_status(self, endpoint_name):
        """_summary_

        Args:
            endpoint_name (_type_): _description_

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


    async def api_set_endpoint_enable(self, endpoint_name):
        endpoint = self.app.endpoints.get(endpoint_name)
        if endpoint:
            endpoint.enable()

    async def api_set_endpoint_disable(self, endpoint_name):
        endpoint = self.app.endpoints.get(endpoint_name)
        if endpoint:
            endpoint.disable()


    async def api_get_endpoint_config(self, endpoint_name):
        endpoint = self.app.endpoints.get(endpoint_name)
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
        return await self.app.job_handler.get_all_workers()


    async def api_get_active_worker_list(self):
        return await self.app.job_handler.get_all_active_workers()


    async def api_get_worker_status(self, worker_auth):
        status = await self.app.job_handler.get_worker_state(worker_auth)
        if status:
            return status.value


    async def admin_set_worker_online(self, worker_auth):
        return await self.app.job_handler.activate_worker(worker_auth)


    async def admin_set_worker_offline(self, worker_auth):
        return await self.app.job_handler.deactivate_worker(worker_auth)
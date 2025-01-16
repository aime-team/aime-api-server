class AdminBEInterfaceImpl(AdminInterface):
    # -> wird von Admin BE realisiert



class AdminInterface():
    """AIME API Server AdminInterface provided by API Server

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
        pass

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


    #### endpoint management
    def api_get_endpoint_list(self):
        # Implemented by API Server
        # list of known endpoints        
        pass

    def api_endpoint_status(self, endpoint_name):
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
        pass

    def api_add_endpoint(self, endpoint_name):
        # Implemented by API Server (later)
        pass

    def api_delete_endpoint(self, endpoint_name):
        # Implemented by API Server (later)
        pass

    def api_set_endpoint_enable(self, endpoint_name, enable):
        # Implemented by API Server
        pass

    def api_get_enpoint_config(self, endpoint_name):
        # Implemented by API Server
        pass

    def api_set_endpoint_config(self, endpoint_name, config):
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


    # worker management
    def api_get_worker_list(self):
        # Implemented by API Server
        # list of current work online      
        pass


    def api_get_worker_status(self, worker_id):
        # Implemented by API Server
        # list of current work online      
        pass

    def admin_set_worker_online(self, worder_id):
        # Implemented by API Server
        # list of current work online      
        pass


    def admin_set_worker_offline(self, worder_id):
        # Implemented by API Server
        # list of current work online      
        pass

Server configuration
~~~~~~~~~~~~~~~~~~~~


The server configuration file model_api_server.cfg is used to set server related parameters and can be found in the root directory of this repository.
Is it divided to certain sections explained in detail below.

The basic server parameters like its address and the location of the endpoint config files are set in the section [SERVER]:

.. code-block:: toml

    [SERVER]
    # basic HTTP server configuration
    port = 0000
    host = "0.0.0.0"
    endpoint_configs = "./endpoints" # search path or list of endpoint configuration files to load on startup

The section [ADMIN] deals with administrator related settings:

.. code-block:: toml

    [ADMIN]
    # login credentials to admin backend
    user = "admin"
    password = ""

Client related configurations can be done in the section [CLIENTS]:

.. code-block:: toml

    [CLIENTS]
    # client default authorization method (can be overwritten in Endpoint configuration)
    # Available authentification: None, User, IP, Pubkey
    default_authentification = "User"
    # Available authorization: None, Key
    default_authorization = "Key"
    default_authorization_keys = { "aime" = "6a17e2a5b70603cb1a3294b4a1df67da" }
    default_provide_worker_meta_data = true	# default is false; used if not specified in endpoint config
    default_client_request_limit = 0 # Allowed number of requests per client; used if not specified in endpoint config

Settings concerning the workers like job_timeout and default auth keys are to be configured in the section [WORKERS]

.. code-block:: toml

    [WORKERS]
    job_timeout = 60
    # default_auth_key = "5b07e305b50505ca2b3284b4ae5f65d7"


Restrictions certain input data types like the allowed formats can be set in the section [INPUTS]. Be aware that input data recognized in a format not being allowed here will be rejected no matter of the supported formats in the endpoint configuration file!

.. code-block:: toml

    [INPUTS]
    # Allowed formats for all media inputs of certain types. Formats not listed here will be rejected, no matter the supported formats in endpoint config file
    image.format = { allowed = [ 'png', 'jpeg' ] }
    audio.format = { allowed = [ 'wav', 'mp3', 'ogg', 'webm', 'mp4' ] }

In the section [STATIC] the static routes can be redirected to a desired destination.

.. code-block:: toml

    [STATIC]
    # mount static served files, path relativ to location of the configuration file
    # supported types: "file" (default), "scss" (SCSS compiled CSS) and "md" (markdown, will be compiled to HTML)

    # demo endpoints shared resources
    "/model_api/js/model_api.js" = { file = "./frontend/static/js/model_api.js" }
    "/model_api/frontend" = { path = "./frontend/static" }
    "/model_api/css" = { path = "./frontend/scss", compiled_path = "./frontend/static/_compiled_/css", type = "scss" }

    # README and Documentation
    "/" = { file = "./README.md", type = "md", compiled_path = "./frontend/static/_compiled_/html", css_file = "./docs/css/markdown.css" }

    "/docs" = { path = "./docs/build/html/" }
    "/docs/css" = { path = "./docs/css/" }
    "/docs/images" = { path = "./docs/images" }


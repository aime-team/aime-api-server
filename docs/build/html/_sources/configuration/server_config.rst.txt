.. Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
   This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

Server configuration
~~~~~~~~~~~~~~~~~~~~


The server configuration file model_api_server.cfg is used to set server related parameters and can be found in the root directory of this repository.
Is it divided to certain sections explained in detail below.

Basic Server Parameters
^^^^^^^^^^^^^^^^^^^^^^^

The basic server parameters like its address and the location of the endpoint config files are set in the section [SERVER]:

* ``port`` *(int): The port of the AIME API Server*

* ``host`` *(str): The IP address of the AIME API Server*

* ``endpoint_configs`` *(str): The location of the endpoint configuration files.*


*Example:*

.. code-block:: toml

    [SERVER]
    port = 0000
    host = "0.0.0.0"
    endpoint_configs = "./endpoints" # search path or list of endpoint configuration files to load on startup


Administrator Parameters
^^^^^^^^^^^^^^^^^^^^^^^^

The section [ADMIN] deals with administrator backend related settings:

* ``user`` *(str): The name of the administrator*

* ``password`` *(str): The password of the administrator*

Example:

.. code-block:: toml

    [ADMIN]
    user = "admin"
    password = ""

Worker Parameters
^^^^^^^^^^^^^^^^^

* ``default_job_timeout`` *(int): Default timeout in seconds after the worker will receive the response "no_job", if no job was offered*

* ``default_auth_key`` *(str): The default worker authorization key is used if the endpoint configuration file doesn't contain the authorization key*

Settings concerning the workers like job_timeout and default auth keys are to be configured in the section [WORKERS]

Example:

.. code-block:: toml

    [WORKERS]
    default_job_timeout = 60
    default_auth_key = "XXX"


Client Parameters
^^^^^^^^^^^^^^^^^^

Default configuration concerning the clients like its authorization and authentication, if not specified in the endpoint configuration file. To have different behaviour in specific endpoints 

* ``default_authentication`` *(str): Default method for the client login authentication*

  *Available settings:*

  * ``"None"`` *(default): The client login request has no restrictions*
  * ``"User"`` *: The client login request has to contain the name of the user*

* ``default_authorization`` *(str): Default method for the client login authorization*

  *Available settings:*

  * ``"None"`` *(default): The client login request has no restrictions*
  * ``"Key"`` *: The client login request has to contain the name of the user (* ``default_authentication`` *has to be* ``"User"`` *) and the related key listed in* ``default_authorization_keys``

* ``default_provide_worker_meta_data`` *(bool): Whether the client receives meta data about the job from the worker. Default = false*

* ``default_client_request_limit`` *(int): The default maximum allowed number of requests per client. 0 = not limited. Default = 0*

Example:

.. code-block:: toml

    [CLIENTS]
    default_authentication = "User"
    default_authorization = "Key"
    default_authorization_keys = { "aime" = "XXX" }
    default_provide_worker_meta_data = true
    default_client_request_limit = 0

Input Parameters
^^^^^^^^^^^^^^^^

Attribute restrictions of certain input parameter types can be set in the section ``[INPUTS]``. Be aware that all input parameters of that type having attributes with values not being allowed here will be rejected no matter of the supported values in the endpoint configuration file!
 
Example:

.. code-block:: toml

    [INPUTS]
    image.format = { allowed = [ 'png', 'jpeg' ] }
    audio.format = { allowed = [ 'wav', 'mp3', 'ogg', 'webm', 'mp4' ] }


Static Routes
^^^^^^^^^^^^^

In the section ``[STATIC]`` the static routes can be redirected to a desired destination. All destinations here are relative to the location of the configuration file.


* ``file`` *(str): To redirect a single file*

* ``path`` *(str): To redirect a whole path*

* ``compile`` *(str): To compile certain file types to a designated format*

  *Available values:*

  * ``"None"`` *(default): No compilation.*
  * ``"scss"`` *: scss files will be compiled to css and saved in* ``compiled_path`` *.*
  * ``"md"`` *: Markdown files will be compiled to html sand saved in* ``compiled_path`` *with related css file in* ``css_file`` *.*
  
* ``compiled_path`` *(str): Path to save the compiled files*

* ``css_file`` *(str): Destination to the related css files for html compiled files*

Example:

.. code-block:: toml

    [STATIC]
    "/desired/destination/to/the/js/client/interface.js" = { file = "./frontend/static/js/model_api.js" }
    "/desired/destination/to/your/frontend/folder/" = { path = "./frontend/" }
    "/desired/destination/to/your/css/folder" = {compile = "scss", path = "./frontend/scss", compiled_path = "./frontend/static/_compiled_/css", }
    "/desired/destination/to/your/readme.html" = { compile = "md", file = "./destination/to/your/md/readme/README.md", compiled_path = "./destination/to/save/your/compiled/html/", css_file = "./destination/to/your/css/file/md_style.css" }
    "/desired/destination/to/your/documentation/path/" = { path = "./destination/to/your/documentation/path/" }


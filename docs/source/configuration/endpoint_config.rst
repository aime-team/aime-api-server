.. Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
   This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

Endpoint Configuration
~~~~~~~~~~~~~~~~~~~~~~


Basic Endpoint Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^

The basic endpoint parameters like its title, name and the http methods are set in the section ``[ENDPOINT]``.

* ``title`` *(str): The full title of the endpoint*

* ``name`` *(str): The name of the endpoint to address it*

* ``description`` *(str): The full description of the endpoint*

* ``methods`` *(array[str]): The allowed http methods. Available methods:* ``"GET"`` *,* ``"POST"``

* ``version`` *(int): The endpoint version no.*

Example:

.. highlight:: toml
.. code-block:: toml

    [ENDPOINT]
    title = "This is the endpoint title"
    name = "endpoint_name"
    description = "The full description of the endpoint"
    methods = [ "GET", "POST" ]
    version = 0


Worker Parameters
^^^^^^^^^^^^^^^^^

The section ``[WORKER]`` deals with worker related parameters.

* ``job_type`` *(str): The type of jobs the related worker is assigned for*

* ``auth_key`` *(str): The authorization key the worker job request has to contain*

* ``job_timeout`` *(int): Timeout in seconds after the worker will receive the response "no_job", if no job was offered*

Example:

.. highlight:: toml
.. code-block:: toml

    [WORKER]
    job_type = "endpoint_name_job_type_a"
    auth_key = "XXX"
    job_timeout = 60


Client Parameters
^^^^^^^^^^^^^^^^^^

Configuration concerning the clients like its authorization and authentication. If not specified here, the default values from the server configuration file are used.

* ``authentication`` *(str): Method for the client login authentication*

  *Available settings:*

  * ``"None"`` *: The client login request has no restrictions*
  * ``"User"`` *: The client login request has to contain the name of the user*

* ``authorization`` *(str): Method for the client login authorization*

  *Available settings:*

  * ``"None"`` *: The client login request has no restrictions*
  * ``"Key"`` *: The client login request has to contain the name of the user (* ``authentication`` *has to be* ``"User"`` *) and the related key listed in* ``authorization_keys``

* ``authorization_keys`` *(dict): Authorized user name - key pairs* ``{ "name" = "key" }``

* ``provide_worker_meta_data`` *(bool): Whether the client receives meta data about the job from the worker.*

* ``client_request_limit`` *(int): The maximum allowed number of requests per client. 0 = not limited*

Example:

.. highlight:: toml
.. code-block:: toml

    [CLIENTS]
    authentification = "User"
    authorization = "Key"
    authorization_keys = { "aime" = "XXX" }
    client_request_limit = 0
    provide_worker_meta_data = true


Input Parameters
^^^^^^^^^^^^^^^^

All job input parameters will be validated by the AIME API Server for security reasons before getting forwarded to the workers.
The ``[INPUTS]`` section offers configuration of the following attributes to adjust that validation to your needs:

* ``type`` *(str): The most important attribute. Each input parameter needs at least the specification of its type or the related client request will be rejected by the AIME API Server. 
  Also if the specified type doesn't match the recognized type of the parameter and the attribute* ``auto_convert`` *is not set to* ``true`` *(It's* ``false`` *by default).
  Available types:* ``"boolean"`` */* ``"bool"`` *,* ``"string"`` */* ``"str"`` *,* ``"integer"`` */* ``"int"`` *,* ``"float"`` *,* ``"selection"`` *,* ``"image"`` *,* ``"image_list"`` *,* ``"audio"``

All parameter types:
""""""""""""""""""""

* ``required`` *(bool): Whether the parameter needs to be present in the client request or not. Client requests with missing required parameters will be rejected if* ``auto_convert`` *is false.* 
  *If* ``auto_convert`` *is true, required parameters need a default value the parameter will be converted to if missing.*
* ``default`` *(same type as parameter): The value missing required parameters will be converted to.*
* ``auto_convert`` *(bool): Whether invalid parameters will be automatically converted to valid parameters if possible. Default is false.*

Types ``"integer"`` and ``"float"``:
""""""""""""""""""""""""""""""""""""

* ``minimum`` or ``min`` *(int/float): The smallest allowed value. If* ``auto_convert = true`` *, smaller values will be converted to the* ``min`` *value.*
* ``maximum`` or ``max`` *(int/float):The highest allowed value. If* ``auto_convert = true`` *, higher values will be converted to the* ``max`` *value.*
* ``align`` *(int/float): Only multiples of the align value are allowed. If* ``auto_convert = true`` *, parameters with values not aligning will be converted to the nearest aligned value.*

Type ``"string"``:
""""""""""""""""""

* ``max_length`` *(int): The maximum allowed length of the string. If* ``auto_convert = true`` *, longer strings will be cut to the* ``max_length`` *value.*

Type ``"json"``:
""""""""""""""""

For more complex input data like chat contexts there is the input type ``"json"``, allowing to transmit an array of objects. The input data has to be in a valid json format.

* *Example data:* 

    .. highlight:: python
    .. code-block:: python

        json_param = [
            {
                "role": "system",
                "content": "System prompt"
            },
            {
                "role": "user", 
                "content": "User question"
            },
            {
                "role": "assistant", 
                "content": "Assistant answer"
            }
        ]

Type ``"selection"``:
"""""""""""""""""""""
If there are only certain values supported by the worker, the type ``"selection"`` is the best choice.

* ``supported`` *(array): The array of supported values. If* ``auto_convert = true`` *, different values will be converted to the* ``default`` *value 
  or the first element of the* ``supported`` *array, if no* ``default`` *value is found.*


Types ``"image"``, ``"image_list"`` and ``"audio"``:
"""""""""""""""""""""""""""""""""""""""""""""""""""""

* ``format`` *(str): The format supported by the workers* 

  * *Available values for the type* ``"audio"`` *:* ``"wav"`` *,* ``"mp3"`` *,* ``"ogg"`` *,* ``"webm"`` *,* ``"mp4"``
  * *Available values for the type* ``"image"`` *or* ``"image_list"`` *:* ``"jpeg"`` *,* ``"jpg"`` *,* ``"png"``
* ``color_space`` *(str): The color space of images supported by the workers. Available values:* ``"rgb"`` *,* ``"cmyk"`` *,* ``"ycbcr"``
* ``size`` *(array): The size of images [width, height] in pixel*
* ``sample_rate`` *(int): The sample rate in Hz of the audio data supported by the workers*
* ``sample_bit_depth`` *(int): The sample bit depth in bits per sample of audio data supported by the workers*
* ``audio_bit_rate`` *(int): The audio bit rate in bits/second supported by the workers*
* ``channels`` *(int): The number of channels (Mono=1, Stereo=2, etc.) of audio data supported by the workers*
* ``duration`` *(int): The duration in seconds of audio data supported by the workers*


Since the attributes of media data need specifications for each attribute seperately, we use nested attributes to do so. That means each attribute above will be configured using the following attributes:

* ``supported`` *(array): Values supported by the workers. Values not listed here will be rejected by the AIME API Server, if* ``auto_convert`` *is false.*
* ``auto_convert`` *(bool): Whether invalid parameters will be automatically converted to valid parameters if possible. Default is false*
* ``default`` *(same type as parent attribute): If* ``auto_convert = true`` *parameters with values not listed in* ``supported`` *, will be converted to the* ``default`` *value.*
* ``minimum`` or ``min`` *(int/float): The smallest allowed value. If* ``auto_convert = true`` *, parameters with smaller values will be converted to the* ``min`` *value.*
* ``maximum`` or ``max`` *(int/float):The highest allowed value. If* ``auto_convert = true`` *, parameters with higher values will be converted to the* ``max`` *value.*
* ``align`` *(int): Only multiples of the align value are allowed. If* ``auto_convert = true`` *, parameters with values not aligning will be converted to the nearest aligned value.*
* ``resize_method`` *(str): The method to use for resizing images. Availabe values:* ``"crop"`` and ``"scale"``


Example:

.. highlight:: toml
.. code-block:: toml

    [INPUTS]
    integer_param = { type = "integer", min = 0, max = 10, default = 1, auto_convert = true }
    float_param = { type = "float", minimum = 0.0, maximum = 10.0, default = 1.0, auto_convert = true }
    string_param = { type = "string", max_length = 200, auto_convert = true }
    json_param = { type = "json", default = [] }

    selection_string_param.type = "selection"
    selection_string_param.supported = [ "option_1", "option_2", "option_3" ]
    selection_string_param.default = "option_2"
    selection_string_param.auto_convert = true

    selection_int_param.type = "selection"
    selection_int_param.supported = [ 1, 2, 4, 8, 16 ]
    selection_int_param.default = 8
    selection_int_param.auto_convert = true

    audio_param.type = "audio"
    audio_param.format = { supported = [ "mp3", "wav" ], default = "wav", auto_convert = true } # bits per sample
    audio_param.sample_rate = { supported = [ 16000 ], default = 16000, auto_convert = true } # in Hz
    audio_param.sample_bit_depth = { supported = [ 16, 32 ], default = 16, auto_convert = true }
    audio_param.audio_bit_rate = { max = 192000, auto_convert = true } # in bits/s
    audio_param.channels = { supported = [ 1 ], default = 1, auto_convert = true }
    audio_param.duration = { max = 30, auto_convert = true } # in seconds

    image_param.type = "image"
    image_param.format = { supported = [ "JPG", "PNG" ], default = "JPG", auto_convert = true }
    image_param.color_space = { supported = [ "RGB" ], default = "RGB", auto_convert = true }

    image_list_param.type = "image_list"
    image_list_param.format = { supported = [ "JPG", "PNG" ], default = "JPG", auto_convert = true }
    image_list_param.color_space = { supported = [ "RGB" ], default = "RGB", auto_convert = true }
    

Output Parameters
^^^^^^^^^^^^^^^^^

Similar to the input parameters also the output parameters need to be declared. Job result parameters coming from the worker not being listed in the section ``[OUTPUTS]`` won't be forwarded to the clients. 

Example:

.. highlight:: toml
.. code-block:: toml

    [OUTPUTS]
    text = { type = "string" }
    num_generated_tokens = { type = "integer" }
    model_name = { type = "string" }

Progress
^^^^^^^^
The AIME API Server offers the possibility to transmit data between the workers and the clients during ongoing worker computations.
Equivalent to the input and output parameters, the progress parameters need to be declared in the subsection ``[OUTPUTS]``. (Currently only progress outputs are implemented)

Example:

.. highlight:: toml
.. code-block:: toml

    [PROGRESS]

        [PROGRESS.OUTPUTS]
        text = { type = "string" }
        num_generated_tokens = { type = "integer" }


Static Routes
^^^^^^^^^^^^^

In the section ``[STATIC]`` the static routes of your endpoint can be redirected to a desired destination the same way as in the server configuration files. All destinations here are relative to the location of the configuration file. Be aware that overwriting routes already declared in the server configuration will raise errors.


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

.. highlight:: toml
.. code-block:: toml

    [STATIC]
    "/your_endpoint_name/" = { file = "./destination/of/your/js/client/index.html" }
    "/your_endpoint_name/desired/destination/to/your/js/client/path/" = { path = "./destination/to/your/js/client/path/" }
    "/your_endpoint_name/desired/destination/to/your/css/style.css" = { file = "./destination/to/your/css/style.css" }


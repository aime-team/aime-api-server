AIME API Benchmark
===========================

Benchmark tool to test, monitor and compare the performance of running GPU workers with the AIME API Server. 
Sends a given number of asynchronous requests using the python client interface.

**Start**

Start the benchmark tool from the root directory of the AIME API Server repo with:

.. highlight:: shell
.. code-block:: shell

    python3 run_api_benchmark.py


Optional command line parameters:


* ``[-as, --api_server]`` *: Address of the AIME API Server. Default:* ``http://0.0.0.0:7777``

* ``[-tr, --total_requests]`` *: Total number of requests. Choose a multiple of the worker's batchsize to have a full last batch. Default:* ``4``

* ``[-cr, --concurrent_requests]`` *: Number of concurrent asynchronous requests limited with asyncio.Semaphore(). Default:* ``40``

* ``[-cf, --config_file]`` *: To change address of endpoint config file to get the default values of the job parameters.*

* ``[-ep, --endpoint_name]`` *: Name of the endpoint. Default:* ``llama2_chat``
                           
* ``[-ut, --unit]`` *: Unit of the generated objects. Default: "tokens" if endpoint_name is "llama2_chat" else "images"*

* ``[-t, --time_to_get_first_batch_jobs]`` *: Time in seconds after start to get the number of jobs in the first batch. Default:* ``4``

* ``[-u, --user_name]`` *: User name to login on AIME API Server. Default:* ``aime``

* ``[-k, --login_key]`` *: Login key related to the user name received from AIME to login on AIME API Server. Default:* ``6a17e2a5b70603cb1a3294b4a1df67da``

* ``[-nu, --num_units]`` *: Number of units to generate. Images for stable_diffusion_xl_txt2img. Default:* ``1``

.. toctree::
    :maxdepth: 2
    :hidden:

    Start<self>
    Source Documentation <doc_benchmark>
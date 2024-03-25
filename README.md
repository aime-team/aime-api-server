---
Title: AIME API Server
---

![AIME API Server](/docs/images/aime_api_banner.jpg "AIME API Server"){: width="100%" style="margin-bottom:60px;"}

# AIME API Server - Scalable Model Inference API Server

With AIME API one deploys deep learning models (Pytorch, Tensorflow) through a job queue as scalable API endpoint capable of serving millions of model inference requests.

Turn a console Python script to a secure and robust web API acting as your interface to the mobile, browser and desktop world.

## Features

* Fast - asynchronous and multi process API server
* Scalable & Robust- distributed cluster ready architecture
* Secure - type safe interface and input validation
* Aggregates API requests to GPU batch jobs for maximum throughput
* Easy integratable into exisiting Python and Tensorflow projects
* High performance image and audio input/ouput conversion for common web formats
* Pythonic - easily extendable in your favourite programming language

## Overview of the AIME API Architecture

The AIME API server solution implements a distributed server architecture with a central API Server communicating through a job queue with a scalable GPU compute cluster. The GPU compute cluster can be heterogeneous and distributed at different locations without requiring an interconnect.

![AIME API Architecture](/docs/images/aime_api_architecture.png "AIME API Architecture")


### AIME API Server

The central part is the [API Server](https://github.com/aime-team/aime-api-server){:target="_blank"}, an efficient asynchronous HTTP/HTTPS web server which can be used stand-alone web server or integrated into Apache, NGINX or similar web servers. It takes the client requests, load balances the requests and distributes them to the API compute workers.

### Compute Workers

The model compute jobs are processed through so called compute workers which connect to the API server through a secure HTTPS interface. 

You can easily turn your existing Pytorch and Tensorflow script into an API compute worker by integrating the [AIME API Worker Interface](https://github.com/aime-team/aime-api-worker-interface){:target="_blank"}.

### Clients

Clients, like web browsers, smartphones, desktop apps can easily integrating model inference API calss with the [AIME API Client Interfaces](https://github.com/aime-team/aime-api-client-interfaces){:target="_blank"}.


## Example Endpoints

To illustrate the usage and capabilities of AIME API we currently run following demo api services:

### LLaMa2 Chat

[![AIME LLaMa2 Chat Demo](/docs/images/aime_api_demo-llm-chat_clrd.jpg "AIME LLaMa2 Chat Demo"){: width="450"}](/#llama2-chat){:target="_parent"}

Chat with 'Dave', our LLaMa2 based chat-bot.

* AIME Demo Server: [LLama2 Chat](https://api.aime.info/#llama2-chat){:target="_parent"}
* Your Local Server: [LLama2 Chat](/llama2-chat/){:target="_parent"}
* Source: [https://github.com/aime-labs/llama2_chat](https://github.com/aime-labs/llama2_chat){:target="_blank"}

### Stable Diffusion XL

[![AIME Stable Diffusion XL Demo](/docs/images/aime_api_demo-seamless-translate_clrd.jpg "AIME Stable Diffusion XL Demo"){: width="450"}](/#sdxl-txt2img){:target="_parent"}

Create photo realistic images from text prompts.

* AIME Demo Server: [Stable Diffusion XL](https://api.aime.info//#sdxl-txt2img){:target="_parent"}
* Your Local Server: [Stable Diffusion XL](/sdxl-txt2img/){:target="_parent"}
* Source: [https://github.com/aime-labs/stable_diffusion_xl](https://github.com/aime-labs/stable_diffusion_xl){:target="_blank"}

### Seamless Communication

[![AIME Seamless Communication Demo](/docs/images/aime_api_demo-sdxl_clrd.jpg "AIME Seamless Communication Demo"){: width="450"}](/#sc-m4tv2){:target="_parent"}

Translate between 36 languages in near realtime: Text-to-Text, Speech-to-Text, Text-to-Speech and Speech-to-Speech! 

* AIME Demo Server: [Seamless Communication](https://api.aime.info/#sc-m4tv2){:target="_parent"}
* Your local Server: [Seamless Communication](/sc-m4tv2/){:target="_parent"}
* Source: [https://github.com/aime-labs/seamless_communication](https://github.com/aime-labs/seamless_communication){:target="_blank"}


## How to setup and start the AIME API Server

### Setup the environment

We recommend creating a virtual environment for local development. Create and activate a virtual environment, like 'venv' with:

```bash
python -m venv venv
source ./venv/bin/activate
```

Download or clone the AIME API server:

```bash
git clone --recurse-submodules https://github.com/aime-team/aime-api-server.git
```

Alternative, for excluding [Worker interface](https://github.com/aime-team/aime-api-worker-interface) and [Client interfaces](https://github.com/aime-team/aime-api-client-interfaces) submodules, which are not needed to run the API server itself, use:

```bash
git clone https://github.com/aime-team/aime-api-server.git 
```

Then install required pip packages:

```bash
pip install -r requirements.txt
```

### Optional: install ffmpeg (required for image and audio conversion)

Ubuntu/Debian:

```bash
sudo apt install ffmpeg
```

### Starting the server

To start the API server run:

```bash
python3 run api_server.py [-H HOST] [-p PORT] [-c EP_CONFIG] [--debug]
```

The server is booting and loading the example endpoints configurations defined in the "/endpoints" directory.

When started it is reachable at http://localhost:7777 (or the port given). As default this README.md file is serverd. The example endpoints are available and are taking requests.

The server is now ready to connect corresponding compute workers.


## Compute Workers

You can easily turn your existing Pytorch and Tensorflow script into an API compute worker by integrating the [AIME API Worker Interface](https://github.com/aime-team/aime-api-worker-interface){:target="_blank"}.

Following example workers implementations are available as open source, which easily can be be adapted to similair use cases:

### How to run a LLaMa2 Chat Worker (Large Language Model Chat)

[https://github.com/aime-labs/llama2_chat](https://github.com/aime-labs/llama2_chat){:target="_blank"}


### How to run a Stable Diffusion Worker (Image Generation)

[https://github.com/aime-labs/stable_diffusion_xl](https://github.com/aime-labs/stable_diffusion_xl){:target="_blank"}


### How to run a Seamless Communication Worker (Text2Text, SpeechText, Text2Speech, Speech2Speech)

[https://github.com/aime-labs/seamless_communication](https://github.com/aime-labs/seamless_communication){:target="_blank"}

## Available Client Interfaces

### Javascript

Simple single call example for an AIME API Server request on endpoint LLaMa 2 with Javascript:

```js

function onResultCallback(data) {
	console.log(data.text) // print generated text to console
}

const endpointName = 'llama2_chat';
params = new Object({
	text : 'Your text prompt' 
});

doAPIRequest(endpointName, params, onResultCallback);
```

### Python

Simple synchronous single call example for an AIME API Server request on endpoint LLaMa 2 with Python:

```python

aime_api_client_interface import do_api_request 

api_server_address = 'https://api.aime.info'
endpoint_name = 'llama2_chat'
params = {'text': 'Your text prompt'}

result = do_api_request(api_server_address, endpoint_name, params)
print(result.get('text')) # print generated text to console
```

### More to come...

We are currently working on sample interfaces for: iOS, Android, Java, PHP, Ruby, C/C++, 

## Documentation

For more information about the AIME read our blog article about [AIME API](https://www.aime.info/en/blog/aime-api-server/){:target="_blank"}.

The AIME API is free of charge for AIME customers. Details can be found in the [LICENSE](https://github.com/aime-team/aime-api-server/LICENSE){:target="_blank"} file. We look forward to hearing from you regarding collaboration or licensing on other devices: hello@aime.info.

Or consult the [AIME API documentation](https://api.aime.info/docs/index.html){:target="_blank"}.

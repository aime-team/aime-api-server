---
Title: AIME API Server
---

# AIME API Server - Scalable Model Inference API Server

With AIME API one deploys deep learning models (Pytorch, Tensorflow) through a job queue as scalable inference API endpoint capable of serving millions of model inference requests.

Turn a console Python script to a secure and robust web API acting as your interface to the mobile, browser and desktop world.

## Features

* Fast - asynchronous and multi process API server
* Scalable & Robust- distributed cluster ready architecture
* Secure - type safe interface and input validation
* Easy integratable into exisiting Python and Tensorflow projects
* High performance image and audio input/ouput conversion for common web formats
* Pythonic - easily extendable in your favourite programming language

## Overview of the AIME API Architecture

The AIME API server solution implements a distributed server architecture with a central API Server communicating through a job queue with a scalable GPU compute cluster. The GPU compute cluster can be heterogeneous and distributed at different locations without requiring an interconnect.

![AIME API Architecture](/docs/images/aime_api_architecture.png "AIME API Architecture")


### AIME API Server

The central part is the [API Server](https://github.com/aime-team/aime-api-server), an efficient asynchronous HTTP/HTTPS web server which can be used stand-alone web server or integrated into Apache, NGINX or similar web servers. It takes the client requests, load balances the requests and distributes them to the API compute workers.

### Compute Workers

The model compute jobs are processed through so called compute workers which connect to the API server through a secure HTTPS interface. 

You can easily turn your existing Pytorch and Tensorflow script into an API compute worker by integrating the [AIME API Worker Interface](https://github.com/aime-team/aime-api-worker-interface).

### Clients

Clients, like web browsers, smartphones, desktop apps or other servers using the API as service can send request through a simple, secure and efficient JSON HTTPS interface.


## Example Endpoints

To illustrate the usage and capabilities of AIME API we currently run following demo api servers:

### LLaMa2 Chat

[![AIME LLaMa2 Chat Demo](/docs/images/aime_llama2_chat.jpg "AIME LLaMa2 Chat Demo")](https://api.aime.info/llama2_chat.html)

Chat with 'Dave', our LLaMa2 based chat-bot.

* Demo: [LLama2 Chat](https://api.aime.info/llama2_chat.html)
* Source: [https://github.com/aime-labs/llama2_chat](https://github.com/aime-labs/llama2_chat)

### Stable Diffusion XL

[![AIME Stable Diffusion XL Demo](/docs/images/aime_stable_diffusion_xl.jpg "AIME Stable Diffusion XL Demo")](https://api.aime.info/sdxl-txt2img/)

Create photo realistic images from text prompts.

* Demo: [Stable Diffusion XL](https://api.aime.info/sdxl-txt2img/)
* Source: [https://github.com/aime-labs/stable_diffusion_xl](https://github.com/aime-labs/stable_diffusion_xl)

### Seamless Communication

[![AIME Seamless Communication Demo](/docs/images/aime_seamless_communication.jpg "AIME Seamless Communication Demo")](https://api.aime.info/sc-m4tv2/)

Translate between 36 languages in near realtime: Text-to-Text, Speech-to-Text, Text-to-Speech and Spech-to-Speech! 

* Demo: [Seamless Communication](https://api.aime.info/sc-m4tv2/)
* Source: [https://github.com/aime-labs/seamless_communication](https://github.com/aime-labs/seamless_communication)


## How to setup and start the AIME API Server

### Virtual Environment

We recommend creating a virtual environment for local development:
```bash
python -m venv venv
source ./venv/bin/activate
```

Create and activate a virtual environment, like 'venv'. Then install required pip packages:

```bash
pip install -r requirements.txt
```

### Install ffmpeg (required for image and audio conversion)

Ubuntu/Debian:

```bash
sudo apt install ffmpeg
```

### Starting the server

To start the API server run:

```bash
python3 run api_server.py [-H HOST] [-p PORT] [-c EP_CONFIG] [--debug]
```

The server is started and is reachable at http://localhost:7777 (or the port given). As default it servers this README.md file and the example endpoints defined in the /endpoints directory.

You are now ready to start up compute workers to connect to your API server.


## Compute Workers

You can easily turn your existing Pytorch and Tensorflow script into an API compute worker by integrating the [AIME API Worker Interface](https://github.com/aime-team/aime-api-worker-interface).

Following example workers implementations are available as open source, which easily can be be adapted to similair use cases:

### How to run a LLaMa2 Chat Worker (Large Language Model Chat)

[https://github.com/aime-labs/llama2_chat](https://github.com/aime-labs/llama2_chat)


### How to run a Stable Diffusion Worker (Image Generation)

[https://github.com/aime-labs/stable_diffusion_xl](https://github.com/aime-labs/stable_diffusion_xl)


### How to run a Seamless Communication Worker (Text2Text, SpeechText, Text2Speech, Speech2Speech)

[https://github.com/aime-labs/seamless_communication](https://github.com/aime-labs/seamless_communication)

## Available Client Interfaces

### Javascript

```js
class ModelAPI {

	constructor(endpoint_name) {
	    this.endpoint_name = endpoint_name;
	    this.client_session_auth_key = null;
	}
}
```

### Python

### More to come...

We are currently working on sample interfaces for: iOS, Android, Java, PHP, Ruby, C/C++, 

## Documentation

See the full documentation at:

More information at:

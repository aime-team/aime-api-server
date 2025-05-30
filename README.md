---
Title: AIME API Server
---

![AIME API Server](/docs/images/aime_api_banner.png "AIME API Server")

# AIME API Server - The Scalable AI Model Inference API Server

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

The central part is the [API Server](https://github.com/aime-team/aime-api-server), an efficient asynchronous HTTP/HTTPS web server which can be used stand-alone web server or integrated into Apache, NGINX or similar web servers. It takes the client requests, load balances the requests and distributes them to the API compute workers.

### Compute Workers

The model compute jobs are processed through so called compute workers which connect to the API server through a secure HTTPS interface. 

You can easily turn your existing Pytorch and Tensorflow script into an API compute worker by integrating the [AIME API Worker Interface](https://github.com/aime-team/aime-api-worker-interface).

### Clients

Clients, like web browsers, smartphones, desktop apps can easily integrating model inference API class with the [AIME API Client Interfaces](https://github.com/aime-team/aime-api-client-interfaces).


## Example Endpoints

To illustrate the usage and capabilities of AIME API we currently run following GenAI (generative AI) demo api services:

### Llama 3.0 / 3.1 / 3.3 Instruct Chat

[![AIME Llama 3.3 Chat Demo](/docs/images/aime_api_demo-llm3-3-chat_banner.png "AIME Llama 3.3 Chat Demo")](https://api.aime.info/llama3-chat/)

Chat with 'Steve', our Llama 3.3 70B based instruct chat-bot.

* AIME Demo Server: [Llama 3.3 Chat](https://api.aime.info/llama3-chat/)
* Your Local Server: [Llama 3.x Chat](/llama3-chat/)
* Source: [https://github.com/aime-labs/llama3_chat](https://github.com/aime-labs/llama3_chat)

### Mixtral 8x7B / 8x22B Instruct Chat

[![AIME Mixtral Chat Demo](/docs/images/aime_api_demo-mixtral-chat_banner.png "AIME Mixtral Instruct Chat Demo")](https://api.aime.info/mixtral-chat/)

Chat with 'Chloe', our Mixtral 8x7B or 8X22B based instruct chat-bot.

* AIME Demo Server: [Mixtral Chat](https://api.aime.info/mixtral-chat/)
* Your Local Server: [Mixtral Chat](/mixtral-chat/)
* Source: [https://github.com/aime-labs/mixtral_chat](https://github.com/aime-labs/mixtral_chat)

### FLUX.1-Dev

[![AIME FLUX.1-Dev Demo](/docs/images/aime_api_demo-flux_banner.png "AIME FLUX.1-Dev Demo")](https://api.aime.info/flux/)

Create photo realistic images with Black Forest Labs FLUX.1-Dev.

* AIME Demo Server: [FLUX.1-Dev](https://api.aime.info/flux/)
* Your Local Server: [FLUX.1-Dev](/flux/)
* Source: [https://github.com/aime-labs/flux](https://github.com/aime-labs/flux)

### Stable Diffusion 3

[![AIME Stable Diffusion 3 Demo](/docs/images/aime_api_demo-sd3_banner.png "AIME Stable Diffusion 3 Demo")](https://api.aime.info/sd3/)

Create photo realistic images with Stable Diffusion 3.

* AIME Demo Server: [Stable Diffusion 3](https://api.aime.info/sd3/)
* Your Local Server: [Stable Diffusion 3](/sd3/)
* Source: [https://github.com/aime-labs/stable_diffusion_3](https://github.com/aime-labs/stable_diffusion_3)


### Seamless Communication

[![AIME Seamless Communication Demo](/docs/images/aime_api_demo-seamless-translate_banner.png "AIME Seamless Communication Demo")](https://api.aime.info/sc-m4tv2/)

Translate between 36 languages in near realtime: Text-to-Text, Speech-to-Text, Text-to-Speech and Speech-to-Speech! 

* AIME Demo Server: [Seamless Communication](https://api.aime.info/sc-m4tv2/)
* Your local Server: [Seamless Communication](/sc-m4tv2/)
* Source: [https://github.com/aime-labs/seamless_communication](https://github.com/aime-labs/seamless_communication)


### Implementation for following model endpoints are also available

#### Stable Diffusion 3.5

Create photo realistic images from text prompts.

* Local Endpoint: [Stable Diffusion 3.5](/stable_diffusion_3_5/)
* Worker Implementation: [https://github.com/aime-labs/aime-api_stable_diffusion_3_5](https://github.com/aime-labs/aime-api_stable_diffusion_3_5)

#### Stable Diffusion XL

Create photo realistic images from text prompts.

* Local Endpoint: [Stable Diffusion XL](/sdxl-txt2img/)
* Worker Implementation: [https://github.com/aime-labs/stable_diffusion_xl](https://github.com/aime-labs/stable_diffusion_xl)

#### Llama2 Chat

Chat with 'Dave', the Llama2 based chat-bot. 

* Local Endpoint: [LLama2 Chat](/llama2-chat/)
* Worker Implementation: [https://github.com/aime-labs/llama2_chat](https://github.com/aime-labs/llama2_chat)

#### Tortoise TTS

Tortoise TTS: high quality Text-To-Speech Demo 

* Local Endpoint: [Tortoise TTS](/tts-tortoise/)
* Worker Implementation: [https://github.com/aime-labs/tortoise-tts](https://github.com/aime-labs/tortoise-tts)


## How to setup and start the AIME API Server

### Setup the environment

We recommend creating a virtual environment for local development. Create and activate a virtual environment, like 'venv' with:

```bash
python3 -m venv venv
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
python3 run api_server.py [-H HOST] [-p PORT] [-c EP_CONFIG] [--dev]
```

The server is booting and loading the example endpoints configurations defined in the "/endpoints" directory.

When started it is reachable at http://localhost:7777 (or the port given). As default this README.md file is serverd. The example endpoints are available and are taking requests.

The server is now ready to connect corresponding compute workers.


## Compute Workers

You can easily turn your existing Pytorch and Tensorflow script into an API compute worker by integrating the [AIME API Worker Interface](https://github.com/aime-team/aime-api-worker-interface).

Following example workers implementations are available as open source, which easily can be be adapted to similair use cases:

### How to run a Llama3 Chat Worker (Large Language Model Chat)

[https://github.com/aime-labs/llama3_chat](https://github.com/aime-labs/llama3_chat)


### How to run a Stable Diffusion Worker (Image Generation)

[https://github.com/aime-labs/stable_diffusion_xl](https://github.com/aime-labs/stable_diffusion_xl)


### How to run a Seamless Communication Worker (Text2Text, SpeechText, Text2Speech, Speech2Speech)

[https://github.com/aime-labs/seamless_communication](https://github.com/aime-labs/seamless_communication)

## Available Client Interfaces

### Javascript

Simple single call example for an AIME API Server request on endpoint LlaMa 2 with Javascript:

```html

<script src="/js/model_api.js"></script>
<script>
function onResultCallback(data) {
	console.log(data.text) // print generated text to console
}

params = new Object({
	text : 'Your text prompt' 
});

doAPIRequest('llama2_chat', params, onResultCallback, 'user_name', 'user_key');
</script>
```

### Python

Simple synchronous single call example for an AIME API Server request on endpoint LlaMa 2 with Python:

```python

aime_api_client_interface import do_api_request 

params = {'text': 'Your text prompt'}

result = do_api_request('https://api.aime.info', 'llama2_chat', params, 'user_name', 'user_key')
print(result.get('text')) # print generated text to console
```

### More to come...

We are currently working on sample interfaces for: iOS, Android, Java, PHP, Ruby, C/C++, 

## Documentation

For more information about the AIME read our [blog article](https://www.aime.info/blog/en/aime-api-server/) about [AIME API](https://api.aime.info/)

The AIME API is free of charge for AIME customers. Details can be found in the [LICENSE](https://github.com/aime-team/aime-api-server/blob/main/LICENSE) file. We look forward to hearing from you regarding collaboration or licensing on other devices: hello@aime.info.

Or consult the [AIME API documentation](https://api.aime.info/docs/index.html).

Title: AIME Model API

# AIME Model API

Deploying Pytorch/Tensorflow models through a job queue as scalable Web-API endpoint made easy.

## Features

* Fast - asynchronous and multi process API server
* Scalable - cluster ready architecture
* Secure & Robust - type safe interface and input validation
* Easy integratable into exisiting Python and Tensorflow projects
* High performance intergrated image and audio processing and conversion for common web formats
* Pythonic - easily extendable in your favourite programming language

## Illustration of the architecture

![Alt text](/docs/images/image.jpg "AIME API Architecture")


## Example Endpoints

Available example endpoints including workers:

* [API Example](/example_api/index.html)
* [LLama2 Chat](/llama2_chat.html)
* [LLama Chat](/llama_chat.html)
* [Stable Diffusion XL](/sdxl-txt2img/)
* [Stable Diffusion](/stable_diffusion_txt2img.html)
* [Seamless Communication](/sc-m4tv2/)


## API Server Setup

How to start up the API Server.

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

### Install ffmpeg

Ubuntu/Debian:

```bash
sudo apt install ffmpeg
```

### Starting the server

To start the API server run:

```bash
python3 run api_server.py [-H HOST] [-p PORT] [-c EP_CONFIG] [--debug]
```

### Connecting it to Apache, NGinx, etc.


## Compute Workers

### How to run a Stable Diffusion Worker

Create an AIME ML container:

```bash
mlc-create mycontainer Pytorch 2.0.1
```

Once done open the container with:

```bash
mlc-open mycontainer
```

Install required packages from apt-get in AIME ML container:
```bash
sudo apt-get install libglib2.0-0 libsm6 libxrender1 libfontconfig1
```
Navigate to /workspace/aime-ml-api/endpoints/stable_diffusion/worker_implementation/ and install the required pip packages:
```bash
cd /workspace/aime-ml-api/endpoints/stable_diffusion/worker_implementation/
pip install -r requirements.txt
```
Download and unzip checkpoint
```bash
sudo apt install curl
curl http://download.aime.info/public/models/stable-diffusion-v1-5-emaonly.zip
sudo apt install unzip unzip stable-diffusion-v1-5-emaonly.zip
```


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

### PHP

### Web

### NodeJs

### HTTP (Curl)

### iOS

### Android

### Java

### Ruby

### C/C++


## How to implement your custom API endpoint and worker

### Define Endpoint

### Description of Endpoint.cfg

### Worker Implementation

#### API Worker Interface

#### How to implement a Pytorch Worker

#### How to implement a Tensorflow Worker

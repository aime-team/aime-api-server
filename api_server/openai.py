# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from sanic.log import logging
from sanic.response import json as sanic_json

import json
from ujson import dumps
from datetime import datetime

from .job_queue import JobState

import asyncio


class OpenAI():
    """AIME API endpoint

    Args:
        app (APIServer): Instance of APIServer()
        config_file (str): Endpoint config file path.
    """    
    logger = logging.getLogger('API')
    models = {}

    def __init__(self, app):
        self.app = app

        if not app.openai_config.get("enable_v1_api", False):
            OpenAI.logger.info(f'--- OpenAI Layer not enabled -> doing nothing')
            return

        OpenAI.logger.info(f'------ Initialising OpenAI Layer')
        OpenAI.models = app.openai_config.get("MODELS", {})
        app.add_route(self.v1_models, "/v1/models", methods=["POST", "GET"], name="v1_models")
        app.add_route(self.v1_chat_completions, "/v1/chat/completions", methods=["POST", "GET"], name="v1_chat_completions")
        app.add_route(self.v1_responses, "/v1/responses", methods=["POST", "GET"], name="v1_responses")
        app.add_route(self.v1_audio_speech, "/v1/audio/speech", methods=["POST", "GET"], name="v1_audio_speech")
        app.add_route(self.v1_audio_transcriptions, "/v1/audio/transcriptions", methods=["POST", "GET"], name="v1_audio_transcriptions")
        app.add_route(self.v1_image_generations, "/v1/images/generations", methods=["POST", "GET"], name="v1_image_generations")


    def __timestamp(self):
        return int(datetime.utcnow().timestamp())

    def __error_response(self, code, message, http_status=404):
        response = {}
        response["error"] = {
            "message": message,
            "type": "invalid_request_error",
            "param": None,
            "code": code,
          }
        
        OpenAI.logger.info(f'OpenAI Error: {str(response["error"])}')
        return sanic_json(response, status=http_status)


    async def check_authorization(self, slug, request):
        headers = request.headers
        authorization = headers.get('authorization', None)
        api_key = None

        OpenAI.logger.info(f'OpenAI {str(slug)}')
        if not authorization or not authorization.startswith("Bearer "):
            return self.__error_response('invalid_api_key', "Incorrect or no API key provided. You can get your API key at https://api.aime.info.", http_status=401), api_key

        api_key = authorization[7:].strip()

        ip_address = headers.get('x-forwarded-for') or request.ip
        validation_errors, error_code = await self.app.validate_api_key(api_key, ip_address)
        if validation_errors:
            return self.__error_response('invalid_api_key', "\n".join(validation_errors), http_status=401), api_key

        return None, api_key


    async def v1_models(self, request):
        """v1 chat 

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        error, api_key = await self.check_authorization("/v1/models", request)
        if error:
            return error

        models = []

        for name, values in OpenAI.models.items():
            created_at = values.get('created_at', 1717700000)
            owned_by = values.get('owned_by', "open-source-model")
            model = {
                "id": name,
                "object": "model",
                "created": created_at,
                "owned_by": owned_by
            }

            models.append(model)

        response = {
          "object": "list",
          "data": models,
        }

        return sanic_json(response)


    async def v1_chat_completions(self, request):
        """v1 chat 

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        error, api_key = await self.check_authorization("/v1/chat/completions", request)
        if error:
            return error
        
        input_params = json.loads(request.body)
        print('input_params', input_params)
        messages = input_params.get('messages', [])
        stream = input_params.get('stream', False)

        default_model = self.app.openai_config.get('fallback_model', None)
        model = input_params.get('model', default_model)
        temperature = input_params.get('temperature', None)
        top_p = input_params.get('top_p', None)
        top_k = input_params.get('top_k', None)
        max_tokens = input_params.get('max_tokens', None)

        # check model availibility
        model_config = OpenAI.models.get(model)
        if not model_config:
            model = default_model
            model_config = OpenAI.models.get(model)
        if not model_config:            
            return self.__error_response('model_not_found', 'Requested model is not supported.')

        chat_context = self.__convert_chat_context_from_openai(messages, model_config.get('default_system_prompt', None))

        if model_config.get('legacy_context_format'):
            last_message = chat_context.pop()
            prompt_input = last_message.get('content')
        else:
            prompt_input = None
            
        request_params = {
            "key": api_key,
            "chat_context": json.dumps(chat_context),
            "wait_for_result": not stream
        }
        if prompt_input:
            request_params['prompt_input'] = prompt_input
        if max_tokens:
            request_params['max_gen_tokens'] = max_tokens
        if temperature:
            request_params['temperature'] = temperature
        if top_p:
            request_params['top_p'] = top_p
        if top_k:
            request_params['top_k'] = top_k
        
        request.body = json.dumps(request_params)

        endpoint_name = model_config.get('endpoint', None)
        endpoint = self.app.endpoints.get(endpoint_name, None)
        if not endpoint:
            return self.__error_response('model_not_found', 'Invalid model, requested model has no defined endpoint.')

        response = await endpoint.api_request(request)
        response = response.raw_body 
        if not response.get('success', False):
            error_message = response.get('error', ['request failed'])[0]
            return self.__error_response('request_failed', error_message)

        job_id = response.get('job_id', "None")
        system_fingerprint = "fp_44709d6fcb"

        if stream:
            response_stream = await request.respond(content_type='text/event-stream')
            
            job = self.app.job_handler.get_job(job_id)
            job_running = True
            prev_len = 0
            while job_running:
                response, error_code = await endpoint.process_api_progress(request, job)
                if response['job_state'] == JobState.PROCESSING or response['job_state'] == JobState.QUEUED:
                    progress_data = response['progress'].get('progress_data', {})
                    text = progress_data.get('text', "")
                    new_len = len(text)

                    if(new_len > prev_len):
                        content = text[prev_len:]
                        prev_len = new_len
                        progress_response = {
                            "id":"chatcmpl-" + job_id,
                            "object":"chat.completion.chunk",
                            "created": self.__timestamp(),
                            "model": model, 
                            "system_fingerprint": system_fingerprint, 
                            "choices":[
                                {
                                    "index":0,
                                    "delta":{"role":"assistant","content": content},
                                    "logprobs":None,
                                    "finish_reason":None
                                }
                            ]
                        }
                        await response_stream.send("data: " + json.dumps(progress_response) + "\n\n")

                    await asyncio.sleep(0.1)

                else:
                    job_running = False
                    response = response.get('job_result', {})
                    text = response.get('text', "")
                    content = text[prev_len:]
                    prompt_tokens =  response.get('prompt_length', 0)
                    completion_tokens = response.get('num_generated_tokens', 0)
                    total_tokens = response.get('current_context_length', 0)

                    response = self.__create_chat_completion_response(model, job_id, content, prompt_tokens, completion_tokens, total_tokens)

                    progress_response = {
                        "id":"chatcmpl-" + job_id,
                        "object":"chat.completion.chunk",
                        "created": self.__timestamp(),
                        "model": model, 
                        "system_fingerprint": system_fingerprint, 
                        "choices":[
                            {
                                "index":0,
                                "delta":{"role":"assistant","content": content},
                                "logprobs":None,
                                "finish_reason":"stop"
                            }
                        ]
                    }

                    await response_stream.send("data: " + json.dumps(progress_response) + "\n\n")

            await response_stream.send("data: [DONE]\n\n")
            await response_stream.eof()
        else:
            content = response.get('text', "")
            prompt_tokens =  response.get('prompt_length', 0)
            completion_tokens = response.get('num_generated_tokens', 0)
            total_tokens = response.get('current_context_length', 0)

            response = self.__create_chat_completion_response(model, job_id, content, prompt_tokens, completion_tokens, total_tokens)

            return sanic_json(response)


    def __convert_chat_context_from_openai(self, messages, default_system_prompt=None):
        chat_context = []
        has_system_prompt = False
        for message in messages:
            role = message.get('role', None)
            if role == 'developer' or role == 'system':
                message['role'] = 'system'
                has_system_prompt = True
            content = message.get('content', {})
            if isinstance(content, list):
                content_converted = list()
                for item in content:
                    content_type = item.get('type')
                    if content_type in ('text', 'output_text'):
                        content_converted.append(item)
                    elif content_type in ('image', 'audio', 'video', 'image_url', 'audio_url', 'video_url'):
                        media_type = content_type.replace('_url', '')
                        url = item.get(content_type, {}).get('url')
                        if url:
                            content_converted.append({media_type: url})
                    else:
                        OpenAI.logger.info(f'OpenAI not supported content type: {content_type}')
                message['content'] = content_converted
            chat_context.append(message)
        if not has_system_prompt and default_system_prompt:
            chat_context.insert(0, { 'role': 'system', 'content': default_system_prompt })

        return chat_context


    def  __create_chat_completion_response(self, model, job_id, content, prompt_tokens, completion_tokens, total_tokens):
        return {
            "id": "chatcmpl-" + job_id,
            "object": "chat.completion",
            "created": self.__timestamp(),
            "model": model,
            "choices": [
                {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "refusal": None,
                    "annotations": []
                },
                "logprobs": None,
                "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "prompt_tokens_details": {
                "cached_tokens": 0,
                "audio_tokens": 0
                },
                "completion_tokens_details": {
                "reasoning_tokens": 0,
                "audio_tokens": 0,
                "accepted_prediction_tokens": 0,
                "rejected_prediction_tokens": 0
                }
            },
            "service_tier": "default"
        }


    async def v1_responses(self, request):
        """v1 responses

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        error, api_key = await self.check_authorization("/v1/responses", request)
        if error:
            return error

        return self.__error_response('not_implemented', 'Service not available', http_status=500)


    async def v1_audio_speech(self, request):
        """v1 audio speech 

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        error, api_key = await self.check_authorization("/v1/audio/speech", request)
        if error:
            return error

        return self.__error_response('not_implemented', 'Service not available', http_status=500)


    async def v1_audio_transcriptions(self, request):
        """v1 audio speech 

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        error, api_key = await self.check_authorization("/v1/audio/transcriptions", request)
        if error:
            return error

        return self.__error_response('not_implemented', 'Service not available', http_status=500)


    async def v1_image_generations(self, request):
        """v1 image generations

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        error, api_key = await self.check_authorization("/v1/image/generations", request)
        if error:
            return error

        return self.__error_response('not_implemented', 'Service not available', http_status=500)

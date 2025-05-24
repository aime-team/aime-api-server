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

    def __init__(self, app):
        self.app = app
        OpenAI.logger.info(f'----------- Initialising OpenAI Layer')        
        app.add_route(self.v1_models, "/v1/models", methods=["POST", "GET"], name="v1_models")
        app.add_route(self.v1_responses, "/v1/responses", methods=["POST", "GET"], name="v1_responses")
        app.add_route(self.v1_chat_completions, "/v1/chat/completions", methods=["POST", "GET"], name="v1_chat_completions")

    def __timestamp(self):
        return int(datetime.utcnow().timestamp())

    def response_error(self, code, message):
        response = {}
        response["error"] = {
            "message": message,
            "type": "invalid_request_error",
            "param": None,
            "code": code,
          }
        return response


    def check_authorization(self, slug, headers):
        authorization = headers.get('authorization', None)
        api_key = None

        OpenAI.logger.info(f'OpenAI {str(slug)}')
        if not authorization and not authorization.startswith("Bearer "):
            return self.response_error('invalid_api_key', "Incorrect or no API key provided. You can get your API key at https://api.aime.info."), api_key

        api_key = authorization[7:].strip()

        return None, api_key


    async def v1_models(self, request):
        """v1 chat 

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        failed, api_key = self.check_authorization("/v1/models", request.headers)
        if failed:
            return sanic_json(failed)

        models = []

        for endpoint in self.app.endpoints.values():
            if endpoint.category == 'chat':
                model = {
                  "id": endpoint.endpoint_name,
                  "object": "model",
                  "created": 1686935002,
                  "owned_by": "open-source-model"
                }

                models.append(model)

        response = {
          "object": "list",
          "data": models,
        }

        return sanic_json(response)

    def _convert_chat_context_from_openai(self, messages):
        last_message = messages.pop()
        prompt_input = last_message.get('content')
        chat_context = []
        for message in messages:
            if message.get('role', None) == 'developer':
                message['role'] = 'system' 
            chat_context.append(message)
        return chat_context, prompt_input

    def _convert_message_to_openai(self, message):
        return message

    async def v1_chat_completions(self, request):
        """v1 chat 

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        failed, api_key = self.check_authorization("/v1/chat/", request.headers)
        if failed:
            return sanic_json(failed)

        OpenAI.logger.info(f'OpenAI {str(api_key)}')

        input_params = json.loads(request.body)
        print(str(input_params))
        messages = input_params.get('messages', [])
        stream = input_params.get('stream', False)
        model = input_params.get('model', None)

        chat_context, prompt_input = self._convert_chat_context_from_openai(messages)

        request.body = json.dumps({
            "key": api_key,
            "chat_context": json.dumps(chat_context),
            "max_gen_tokens": 500,
            "prompt_input": prompt_input,
            "temperature": 0.8,
            "top_k": 40,
            "top_p": 0.9,
            "wait_for_result": not stream
        })

        endpoint = self.app.endpoints[model]
        response = await endpoint.api_request(request)
        response = response.raw_body 

        job_id = response.get('job_id', "None")

        if stream:
            response_stream = await request.respond(content_type='text/event-stream')
            
            job = self.app.job_handler.get_job(job_id)
            job_running = True
            prev_len = 0
            while job_running:
                validation_errors = {}
                response = await endpoint.process_api_progress(request, job, validation_errors)
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
                            "model":"gpt-4o-mini", 
                            "system_fingerprint": "fp_44709d6fcb", 
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

                    response = self.__create_chat_completion_response(job_id, content, prompt_tokens, completion_tokens, total_tokens)

                    progress_response = {
                        "id":"chatcmpl-" + job_id,
                        "object":"chat.completion.chunk",
                        "created": self.__timestamp(),
                        "model":"gpt-4o-mini", 
                        "system_fingerprint": "fp_44709d6fcb", 
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

            response = self.__create_chat_completion_response(job_id, content, prompt_tokens, completion_tokens, total_tokens)

            return sanic_json(response)


    async def v1_responses(self, request):
        """v1 chat 

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        print(str(request.headers))

        failed, api_key = self.check_authorization("/v1/responses/", request.headers)
        if failed:
            return sanic_json(failed)

        job_id = "67ccd2bed1ec8190b14f964abc0542670bb6a6b452d3795b"

        response = {
            "id": "resp_" + job_id,
            "object": "response",
            "created_at": self.__timestamp(),
            "status": "completed",
            "error": None,
            "incomplete_details": None,
            "instructions": None,
            "max_output_tokens": None,
            "model": "gpt-4.1-2025-04-14",
            "output": [
                {
                  "type": "message",
                  "id": "msg_" + job_id,
                  "status": "completed",
                  "role": "assistant",
                  "content": [
                    {
                      "type": "output_text",
                      "text": "In a peaceful grove beneath a silver moon, a unicorn named Lumina discovered a hidden pool that reflected the stars. As she dipped her horn into the water, the pool began to shimmer, revealing a pathway to a magical realm of endless night skies. Filled with wonder, Lumina whispered a wish for all who dream to find their own hidden magic, and as she glanced back, her hoofprints sparkled like stardust.",
                      "annotations": []
                    }
                  ]
                }
            ],
            "parallel_tool_calls": True,
            "previous_response_id": None,
            "reasoning": {
                "effort": None,
                "summary": None
            },
            "store": None,
            "temperature": 1.0,
            "text": {
                "format": {
                  "type": "text"
                }
            },
            "tool_choice": "auto",
            "tools": [],
            "top_p": 1.0,
            "truncation": "disabled",
            "usage": {
                "input_tokens": 36,
                "input_tokens_details": {
                    "cached_tokens": 0
                },
                "output_tokens": 87,
                "output_tokens_details": {
                    "reasoning_tokens": 0
                },
                "total_tokens": 123
            },
            "user": None,
            "metadata": {}
        }

        return sanic_json(response)


    def  __create_chat_completion_response(self, job_id, content, prompt_tokens, completion_tokens, total_tokens):
        return {
            "id": "chatcmpl-" + job_id,
            "object": "chat.completion",
            "created": self.__timestamp(),
            "model": "gpt-4.1-2025-04-14",
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
   

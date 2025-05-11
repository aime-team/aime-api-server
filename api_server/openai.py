# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from sanic.log import logging
from sanic.response import json as sanic_json

import json

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

        api_key = authorization[7:]
        OpenAI.logger.info(f'OpenAI {str(api_key)}')

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

        chat_context = [
            {
                "role":"system",
                "content": "You are a helpful, respectful and honest assistant named Pete. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."
            },
            {
                "role":"user",
                "content": "Hello, Pete."
            },
            {
                "role":"assistant",
                "content":"How can I assist you today?"
            }
        ]

        request.body = json.dumps({
            "key": api_key,
            "chat_context": json.dumps(chat_context),
            "max_gen_tokens": 500,
            "prompt_input": "Hi Pete!",
            "temperature": 0.8,
            "top_k": 40,
            "top_p": 0.9,
            "wait_for_result": False
        })

        response = await self.app.endpoints['llama3_chat'].api_request(request)
        response = response.raw_body 
        print(str(response))

        job_id = response.get('job_id', None)

        response = {
          "id": "chatcmpl-" + job_id,
          "object": "chat.completion",
          "created": 1741569952,
          "model": "gpt-4.1-2025-04-14",
          "choices": [
            {
              "index": 0,
              "message": {
                "role": "assistant",
                "content": "Hello! How can I assist you today?",
                "refusal": None,
                "annotations": []
              },
              "logprobs": None,
              "finish_reason": "stop"
            }
          ],
          "usage": {
            "prompt_tokens": 19,
            "completion_tokens": 10,
            "total_tokens": 29,
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
            "created_at": 1741476542,
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

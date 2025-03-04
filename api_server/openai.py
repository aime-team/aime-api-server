# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from sanic.log import logging
from sanic.response import json as sanic_json

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
        app.add_route(self.v1_chat, "/v1/chat/completions", methods=["POST", "GET"], name="v1_chat_completions")


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

        OpenAI.logger.info(f'OpenAI {str(slug)}')
        if not authorization:
            return self.response_error('invalid_api_key', "Incorrect or no API key provided. You can get your API key at https://api.aime.info.")

        return None


    async def v1_models(self, request):
        """v1 chat 

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        failed = self.check_authorization("/v1/models", request.headers)
        if failed:
            return sanic_json(failed)

        response = {'success': True}        
        return sanic_json(response)



    async def v1_chat(self, request):
        """v1 chat 

        Args:
            request (sanic.request.types.Request): Request from client

        Returns:
            sanic.response.types.JSONResponse: Response to client
        """
        failed = self.check_authorization("/v1/chat/", request.headers)
        if failed:
            return sanic_json(failed)

        response = {'success': True}
        return sanic_json(response)


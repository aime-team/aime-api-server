# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

import argparse

class Flags():

    def __init__(self):
        self.args = self.load_flags()
        self.set_default_values()

    def load_flags(self):
        """Parses arguments and sets global parameters.
        """        
        parser = argparse.ArgumentParser(
            description='AIME ML API Server', formatter_class=argparse.ArgumentDefaultsHelpFormatter
                                        )
        parser.add_argument(
            '-H', '--host', type=str, required=False,
            help='To use different host address than specified in server config file'
                            )
        parser.add_argument(
            '-p', '--port', type=int, required=False, help='To use different port number than specified in server config file'
                            )
        parser.add_argument(
            '-s', '--server_config', type=str, required=False,
            help='Pointer to file from where to load the server config (default aime_api_server.cfg)'
                            )
        parser.add_argument(
            '-c', '--ep_config', type=str, required=False,
            help='To use different directory or file form where to load the config of endpoint.cfg files than specified in server config file'
                            )
        parser.add_argument(
            '--dev', action='store_true', required=False,
            help='Run the server in debug/development mode'
                            )
        parser.add_argument(
            '-wp', '--worker_processes', type=int, default=1, required=False, help='Number of api server worker processes [default 1]'
                            )
        parser.add_argument(
            '--hide_logging', action='store_true', required=False,
            help='Hide logging in console'
                            )
        parser.add_argument(
            '--no_sanic_logger', action='store_true', required=False,
            help='Hide logging in console'
                            )
        parser.add_argument(
            '--no_colour', action='store_true', required=False,
            help='No colours in logger'
                            )
                            
                            
        args = parser.parse_args()
        return args

    def set_default_values(self):

        if not self.args.server_config:
            self.args.server_config = './aime_api_server.cfg'


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
            '-H', '--host', type=str, default="0.0.0.0", required=False,
            help='Host address [default 0.0.0.0]'
                            )
        parser.add_argument(
            '-p', '--port', type=int, default=7777, required=False, help='Port number'
                            )
        parser.add_argument(
            '-s', '--server_config', type=str, required=False,
            help='Pointer to file from where to load the server config (default aime_api_server.cfg)'
                            )
        parser.add_argument(
            '-c', '--ep_config', type=str, required=False,
            help='Pointer to directory or file form where to load the config of endpoint.cfg files'
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
                            
                            
        args = parser.parse_args()
        return args

    def set_default_values(self):
        if not self.args.ep_config:
            self.args.ep_config = './endpoints'
        if not self.args.server_config:
            self.args.server_config = './aime_api_server.cfg'



from sanic_session import Session, InMemorySessionInterface
from api_server.api_server import APIServer
from api_server.flags import Flags
from api_server.utils import copy_js_client_interface_to_frontend_folder

flags = Flags()
args = flags.args
API_NAME = "AIME_API_Server"
app = APIServer(API_NAME, args)


# create sessions
session = Session(app, interface=InMemorySessionInterface())
app.config.PROXIES_COUNT = 1
app.config.KEEP_ALIVE_TIMEOUT = 10


if __name__ == "__main__":
    copy_js_client_interface_to_frontend_folder()
    app.run(host=args.host, port=args.port, debug=args.dev, workers=args.worker_processes)




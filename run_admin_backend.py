from sanic_session import Session, InMemorySessionInterface
from admin_backend.admin_backend import AdminBackend
from api_server.flags import Flags


flags = Flags()
args = flags.args

app = AdminBackend("admin_app")

# create sessions
session = Session(app, interface=InMemorySessionInterface())

app.config.PROXIES_COUNT = 1
app.config.KEEP_ALIVE_TIMEOUT = 10

def main():
    app.run(host=args.host, port=args.port, debug=args.dev)


if __name__ == "__main__":
    main()

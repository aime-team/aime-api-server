# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from sanic_session import Session, InMemorySessionInterface
from api_server.api_server import APIServer
from api_server.utils.misc import copy_js_client_interface_to_frontend_folder
from api_server.admin_interface import MinimumAdminBackendImplementation


API_NAME = "AIME_API_Server"
app = APIServer(API_NAME)

# create sessions
session = Session(app, interface=InMemorySessionInterface())

admin_backend = MinimumAdminBackendImplementation(app, app.args, None)

app.connect_admin_backend(admin_backend)

if __name__ == "__main__":
    copy_js_client_interface_to_frontend_folder()
    app.run(
        host=app.host,
        port=app.port,
        debug=app.args.dev,
        workers=app.args.worker_processes
    )

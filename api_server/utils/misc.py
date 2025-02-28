
import time
from pathlib import Path
import shutil
import uuid
from functools import partial
import asyncio
import base64
from sanic_sass import SassManifest
from sanic.log import logging
from concurrent.futures import ThreadPoolExecutor

from .markdown_compiler import MarkDownCompiler


logger = logging.getLogger('API')
thread_pool = ThreadPoolExecutor()


class StaticRouteHandler:
    def __init__(self, config_file_path, app, endpoint_name=None):
        self.config_file_path = Path(config_file_path)
        self.endpoint_name = endpoint_name if endpoint_name else 'app'
        self.app = app
        self.num = 0


    def setup_file_route(self, slug, route):
        route_path = Path(route.get('path', route.get('file')))
        if route_path:
            if not route_path.is_absolute():
                route_path = (self.config_file_path / route_path).resolve()
            self.app.static(slug, route_path, name=f'{self.endpoint_name}_static{str(self.num)}')
            self.num += 1


    def setup_markdown_route(self, slug, route):
        route_path = route.get('path', route.get('file'))
        compiled_path = (self.config_file_path / route.get('compiled_path')).resolve()
        css_file = route.get('css_file')
        output_file = compiled_path / f'{Path(route_path).stem}.html'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        MarkDownCompiler.compile(route_path, output_file, css_file)
        self.app.static(slug, output_file, name=f'{self.endpoint_name}_static{str(self.num)}')
        self.num += 1


    def setup_scss_route(self, slug, route):
        compiled_path = (self.config_file_path / Path(route.get('compiled_path'))).resolve()
        manifest = SassManifest(slug, str(compiled_path), route.get('path', route.get('file')), css_type='scss')
        manifest.compile_webapp(self.app, register_static=True)
        self.num += 1


    def setup_static_routes(self, static_routes):
        for slug, route in static_routes.items():
            compile_type = route.get('compile')
            if compile_type == 'md':
                self.setup_markdown_route(slug, route)
            elif compile_type == 'scss':
                self.setup_scss_route(slug, route)
            else:
                self.setup_file_route(slug, route)
            self.log_static_info(slug, route)


    def log_static_info(self, slug, route):
        compile_type = route.get('compile')

        if route.get('compiled_path'):
            compiled_path = Path(route.get('compiled_path')).resolve()
        route_path = route.get('path', route.get('file'))
        if compile_type == 'md':
            compile_str = f' ({compile_type} files compiled to html in {compiled_path} with css in {Path(route.get("css_file")).resolve()})'
        elif compile_type == 'scss':
            compile_str = f' ({compile_type} files compiled to css in {compiled_path})'
        else:
            compile_str = ''
        self.app.logger.info(f'Static: {slug} -> {(self.config_file_path / route_path).resolve()}{compile_str}')


class EndpointStatus():

    def __init__(self, endpoint_name):
        self.endpoint_name = endpoint_name
        self.last_request_time = None
        self.num_finished_requests = 0
        self.num_failed_requests = 0
        self.num_aborted_requests = 0


    def get(self):
        pass


class CustomFormatter(logging.Formatter):
    BACKGROUND_AIME_DARK_BLUE = '\033[48;2;35;55;68m'
    AIME_LIGHT_BLUE ='\033[38;2;0;194;218m'
    AIME_RED = '\033[38;2;239;104;104m'
    AIME_BOLD_RED = '\033[1m\033[38;2;239;104;104m'
    AIME_YELLOW = '\033[38;2;255;188;68m'
    AIME_LIGHT_GREEN = '\033[38;2;197;229;199m'
    RESET = '\033[0m'
        

    desc_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    FORMATS = {
        logging.DEBUG: AIME_LIGHT_BLUE + desc_format + RESET,
        logging.INFO: AIME_LIGHT_GREEN + desc_format + RESET,
        logging.WARNING: AIME_YELLOW + desc_format + RESET,
        logging.ERROR: AIME_RED + desc_format + RESET,
        logging.CRITICAL: AIME_BOLD_RED + desc_format + RESET
    }

    def __init__(self, no_colour=False):
        super().__init__()
        self.no_colour = no_colour


    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno) if not self.no_colour else self.desc_format
        formatter = logging.Formatter(log_fmt, datefmt = '%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


async def run_in_executor(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, partial(func, *args, **kwargs))


def shorten_strings(obj, max_length=30):
    if isinstance(obj, dict):
        return {key: shorten_strings(value, max_length) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [shorten_strings(item, max_length) for item in obj]
    elif isinstance(obj, str) and len(obj) > max_length:
        return obj[:max_length] + "..."
    elif isinstance(obj, bytes) and len(obj) > max_length:
        return obj[:max_length] + "..."
    else:
        return obj


def generate_auth_key():
    return str(uuid.uuid4())


def check_if_valid_base64_string(test_string):
    """
    Check if given string is a valid base64-encoded string.

    Args:
        test_string (str): The string to test.

    Returns:
        bool: True if the string is a valid base64-encoded string, False otherwise.
    """
    try:
        body = test_string.split(',')[1] if ',' in test_string else None
        return base64.b64encode(base64.b64decode(body.encode('utf-8'))).decode('utf-8') == body if body else False
    except (TypeError, base64.binascii.Error, ValueError):
        return False

def copy_js_client_interface_to_frontend_folder():
    js_client_interface_folder = Path('./api_client_interfaces/js')

    if js_client_interface_folder.exists():
        js_client_interface_filename = 'model_api.js'
        frontend_folder = Path('./frontend/static/js/')
        logger.info(f'Subrepository "AIME API Client Interfaces" folder in {js_client_interface_folder.parent.resolve()} is present. Javascript client interface {js_client_interface_filename} is copied from {js_client_interface_folder.resolve()} to {frontend_folder.resolve()}.')
        shutil.copy(js_client_interface_folder / js_client_interface_filename, frontend_folder / js_client_interface_filename)



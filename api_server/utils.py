from pathlib import Path
from sanic_sass import SassManifest
from .markdown_compiler import MarkDownCompiler


class StaticRouteHandler:
    def __init__(self, config_file_path, app, endpoint_name=None):
        self.config_file_path = Path(config_file_path)
        self.endpoint_name = endpoint_name if endpoint_name else 'app'
        self.app = app
        self.num = 0


    def setup_file_route(self, slug, route):
        route_path = Path(route.get('path', route.get('file', None)))
        if route_path:
            if not route_path.is_absolute():
                route_path = (self.config_file_path / route_path).resolve()
            self.app.static(slug, route_path, name=f'{self.endpoint_name}_static{str(self.num)}')
            self.num += 1

    def setup_markdown_route(self, slug, route):
        route_path = route.get('path', route.get('file', None))
        compiled_path = (self.config_file_path / route.get('compiled_path')).resolve()
        css_file = route.get('css_file')
        output_file = compiled_path / f'{Path(route_path).stem}.html'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        MarkDownCompiler.compile(route_path, output_file, css_file)
        self.app.static(slug, output_file, name=f'{self.endpoint_name}_static{str(self.num)}')
        self.num += 1

    def setup_scss_route(self, slug, route):
        compiled_path = (self.config_file_path / Path(route.get('compiled_path'))).resolve()
        manifest = SassManifest(slug, str(compiled_path), route.get('path', route.get('file', None)), css_type='scss')
        manifest.compile_webapp(self.app, register_static=True)
        self.num += 1

    def setup_static_routes(self, static_routes):
        for slug, route in static_routes.items():
            route_type = route.get('type', 'file')
            if route_type == 'file':
                self.setup_file_route(slug, route)
            elif route_type == 'md':
                self.setup_markdown_route(slug, route)
            elif route_type == 'scss':
                self.setup_scss_route(slug, route)

            self.log_static_info(slug, route_type, route.get('path', route.get('file')))

    def log_static_info(self, slug, route_type, route_path):
        self.app.logger.info(f'Static: {slug} -> [{route_type}] {route_path}')


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

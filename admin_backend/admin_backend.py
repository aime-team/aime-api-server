from sanic import Sanic
from sanic.response import html
from jinja2 import Environment, PackageLoader, select_autoescape, TemplateNotFound
from sanic_sass import SassManifest

class AdminBackend(Sanic):

    def __init__(self, name):
        super().__init__(name)
        self.init()

    def init(self, args=None):
        env = Environment(
            loader=PackageLoader("admin_backend", "templates"),
            autoescape=select_autoescape(["html", "xml"])
        )

        @self.route("/")
        @self.route("/<path:path>", name="path_route")
        async def index(request, path="index.html"):
            try:
                segment = self.get_segment(request)
                template = env.get_template("home/" + path)
                rendered_template = template.render(segment=segment)
                return html(rendered_template)
            except TemplateNotFound:
                template = env.get_template("home/page-404.html")
                rendered_template = template.render()
                return html(rendered_template, status=404)

        self.static("/static", "admin_backend/static", name="static_admin_backend")

        ## compile SASS files
        #manifest = SassManifest("/model_api/css", "/../templates/_compiled_/css", os.path.dirname(__file__) + "/../templates/vendor/admin_lte/scss", css_type="scss")
        #manifest.compile_webapp(self, register_static=True)

    def get_segment(self, request):
        try:
            segment = request.path.split("/")[-1]
            if segment == "":
                segment = "index"
            return segment
        except:
            return None

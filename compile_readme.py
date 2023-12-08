from api_server.markdown_compiler import MarkDownCompiler


print("Compiling README.md to README.html")

MarkDownCompiler.compile("README.md", "README.html", "./doc/css/markdown.css")

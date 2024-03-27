# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT

from api_server.markdown_compiler import MarkDownCompiler

print("Compiling README.md to README.html")

MarkDownCompiler.compile("README.md", "README.html", "./doc/css/markdown.css")

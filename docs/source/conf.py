# Configuration file for the Sphinx documentation builder.
#
# Copyright (c) AIME GmbH and affiliates. Find more info at https://www.aime.info/api
#
# This software may be used and distributed according to the terms of the AIME COMMUNITY LICENSE AGREEMENT
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os 
import sys 

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../api_client_interfaces/python'))
sys.path.insert(0, os.path.abspath('../../api_worker_interface'))

js_source_path = '../../frontend/static/js'

project = 'AIME API Server'
copyright = '2024, AIME GmbH'
author = 'AIME GmbH'
release = '0.8.0'


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.extlinks',
    'sphinx_js'
]


extlinks = {
    'api_aime_info': ('https://api.aime.info/%s', 'AIME API')
}

templates_path = ['_templates']
exclude_patterns = []

napoleon_google_docstring = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['../css']
html_css_files = ['aime_override.css']
html_logo = '../images/AIME-API_logo_claim.svg'
html_favicon = '../images/AIME-API_logo.svg'
html_theme_options = {
    'logo_only': True,
}

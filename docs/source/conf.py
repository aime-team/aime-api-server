# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os 
import sys 
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../api_client_interfaces/python'))
sys.path.insert(0, os.path.abspath('../../api_worker_interface'))

js_source_path = '../../frontend/static/js'

project = 'AIME API Server'
copyright = '2023, AIME GmbH'
author = 'AIME GmbH'
release = '0.8.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_js'
]

templates_path = ['_templates']
exclude_patterns = []

napoleon_google_docstring = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_css_files = ['../css/aime_override.css']

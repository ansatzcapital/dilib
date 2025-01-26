# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'dilib'
copyright = '2025, author'
author = 'author'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
]

templates_path = ['_templates']
exclude_patterns = [
    '**/dilib.rst',
    '**/modules.rst',
]

language = 'en'

# See https://www.sphinx-doc.org/en/master/usage/markdown.html
source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}

# See https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#auto-generated-header-anchors
myst_heading_anchors = 3

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']

html_theme_options = {
    'collapse_navigation': True,  # Collapses navigation items
    'navigation_depth': 2,        # Adjusts depth of sidebar links
}


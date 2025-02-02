# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------
from __future__ import annotations

from typing import Any

import dilib.version

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "dilib"
copyright = "2025, dilib"  # noqa: A001
author = "dilib"

version = dilib.version.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx.ext.autodoc",
    "sphinx.ext.githubpages",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = [
    "**/dilib.rst",
    "**/modules.rst",
]

language = "en"

# See https://www.sphinx-doc.org/en/master/usage/markdown.html
source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

# See https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#auto-generated-header-anchors
myst_heading_anchors = 3

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_title = "dilib"
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

if "dev" in version:
    version_match = "dev"
else:
    version_match = f"v{version}"

html_theme_options = {
    # Collapses navigation items
    "collapse_navigation": True,
    # Adjusts depth of sidebar links
    "navigation_depth": 2,
    # See https://github.com/pydata/pydata-sphinx-theme/blob/main/docs/conf.py
    "header_links_before_dropdown": 10,
    # Add the dropdown to the navbar
    "navbar_align": "left",
    "navbar_center": ["version-switcher", "navbar-nav"],
    # "show_version_warning_banner": True,
    "switcher": {
        # URL to versions file
        "json_url": "_static/versions.json",
        # Current version
        "version_match": version_match,
    },
    # See https://fontawesome.com/
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/ansatzcapital/dilib",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/dilib",
            "icon": "fa-solid fa-cube",
        },
    ],
}

html_sidebars: dict[str, Any] = {
    "**": []  # No sidebar content for any page
}

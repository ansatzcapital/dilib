#!/bin/bash
set -e

cd "docs"

# Clean up generated RST and HTML files.
rm -rf "build"
rm -rf "source/api/dilib.rst"
rm -rf "source/api/modules.rst"

# Generate API docs.
# NB: Because of an odd choice by Sphinx,
# all args after first one are "exclude pattern".
sphinx-apidoc -o source/api ../dilib ../dilib/tests ../dilib/experimental

# Generate Sphinx output. TODO: Parametrize version.
sphinx-build source build/dilib/latest -W

# Redirect top level to latest.
cp "source/_static/redirect_index.html" "build/dilib/index.html"

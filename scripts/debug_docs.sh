#!/bin/bash
set -e

cd "docs/build"
echo "Local server: http://localhost:8000/dilib"
python -m http.server

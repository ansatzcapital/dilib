#####################################################################
# Composite
#####################################################################

default: fix test

static: ruff mypy pyright

fix: fix-ruff

unit-test: pytest

build: build-python-dist

test: static unit-test

test-matrix:
    pixi run -e test-py38 --frozen --locked just test
    pixi run -e test-py39 --frozen --locked just test
    pixi run -e test-py310 --frozen --locked just test
    pixi run -e test-py311 --frozen --locked just test
    pixi run -e test-py312 --frozen --locked just test
    pixi run -e test-py313 --frozen --locked just test
    pixi run -e test-py314 --frozen --locked just test

#####################################################################
# Common
#####################################################################

run-ci-tests:
    act -j test --container-architecture linux/amd64

gen-docs:
    ./scripts/gen_docs.sh

debug-docs: gen-docs
    ./scripts/debug_docs.sh

#####################################################################
# Python
#####################################################################

ruff:
    ruff format . --check && ruff check .

fix-ruff:
    ruff format . && ruff check . --fix

mypy:
    mypy .

pyright:
    pyright .

pytest:
    pytest .

build-python-dist:
    uv build && twine check dist/*

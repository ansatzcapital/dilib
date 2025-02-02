"""Nox setup.

To run all linters, checkers, and tests:

```bash
nox
```

To run all fixers:

```bash
nox -t fix
```

By default, nox will set up venvs for each session. To use your current
env instead, add `--no-venv` to any command:

```bash
nox --no-venv
```

By default, nox will recreate venvs for each session. To reuse your existing
env instead, add `--reuse`/`-r` to any command:

```bash
nox --reuse
```

To run all static linters and checkers:

```
nox -t static
```

To pick a particular session, e.g.:

```bash
nox --list
nox -s fix_ruff
nox -s pytest -- -k test_name
```

To do an editable install into your current env:

```bash
nox -s develop
```

All sessions:

```
- print_env -> Print env info for debugging.
* mypy -> Run mypy type checker.
* pyright -> Run pyright type checker.
* pytest -> Run pytest.
* ruff -> Run ruff formatter and linter checks.
- fix_ruff -> Fix some ruff formatter and linter issues.
- build -> Build Python wheel.
- develop -> Install local dir into activated env using editable installs.
- gen_docs -> Generate docs outputs.
- debug_docs -> Run local server to debug doc outputs.

sessions marked with * are selected, sessions marked with - are skipped.
```

See https://nox.thea.codes/en/stable/index.html for more.
"""

import sys
from typing import Final

import nox
import nox.virtualenv

PYTHON_PROJECT_NAME: Final[str] = "dilib"

nox.options.default_venv_backend = "uv"

# Hack to fix tags for non-defaulted sessions (otherwise, running
# `nox -t fix` won't pick up any sessions)
if any(arg.startswith("fix") for arg in sys.argv):
    nox.options.sessions = ["fix_ruff"]
else:
    nox.options.sessions = ["ruff", "mypy", "pyright", "pytest"]


def is_isolated_venv(session: nox.Session) -> bool:
    """Indicates that the session is being run in an isolated env.

    I.e., the user has not set `--no-venv`.

    If the user uses their development (non-isolated) venv,
    then nox will (correctly) refuse to install packages, unless forced to.
    """
    return not isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv)


def prepare(session: nox.Session, extras: str = "all") -> None:
    """Help debugging in CI context."""
    if is_isolated_venv(session):
        session.install("-e", f".[{extras}]")


@nox.session()
def print_env(session: nox.Session) -> None:
    """Print env info for debugging."""
    prepare(session)

    session.run("python", "--version")
    session.run("uv", "pip", "list")


@nox.session(tags=["static", "typecheck"])
def mypy(session: nox.Session) -> None:
    """Run mypy type checker."""
    prepare(session)

    session.run("mypy", ".")


@nox.session(tags=["static", "typecheck"])
def pyright(session: nox.Session) -> None:
    """Run pyright type checker."""
    prepare(session)

    env = {"PYRIGHT_PYTHON_VERBOSE": "1"}
    # Enable for debugging
    if False:
        env["PYRIGHT_PYTHON_DEBUG"] = "1"

    session.run("pyright", ".", env=env)


@nox.session(tags=["test"])
def pytest(session: nox.Session) -> None:
    """Run pytest."""
    prepare(session)

    session.run("pytest", ".", *session.posargs)


@nox.session(tags=["lint", "static"])
def ruff(session: nox.Session) -> None:
    """Run ruff formatter and linter checks."""
    prepare(session)

    session.run("ruff", "format", ".", "--check")
    session.run("ruff", "check", ".")


@nox.session(tags=["fix"])
def fix_ruff(session: nox.Session) -> None:
    """Fix some ruff formatter and linter issues."""
    prepare(session)

    session.run("ruff", "format", ".")
    session.run("ruff", "check", ".", "--fix")


@nox.session()
def build(session: nox.Session) -> None:
    """Build Python wheel."""
    prepare(session)

    session.run("python", "-m", "build", "--wheel")
    session.run("twine", "check", "dist/*")


@nox.session(venv_backend="none")
def develop(session: nox.Session) -> None:
    """Install local dir into activated env using editable installs."""
    # We install using compatibility mode for VS Code
    # to pick up the installation correctly.
    # See https://setuptools.pypa.io/en/latest/userguide/development_mode.html#legacy-behavior.
    session.run(
        "uv",
        "pip",
        "install",
        "-e",
        ".[all]",
        "--config-settings",
        "editable_mode=compat",
    )


# # This was used originally to bootstrap the docs, but it's no longer
# # usable as we've made custom edits.
# @nox.session(tags=["docs"])
# def bootstrap_docs(session: nox.Session) -> None:
#     """Boostrap initial docs files."""
#     session.run(
#         "sphinx-quickstart",
#         "docs",
#         "--project",
#         PYTHON_PROJECT_NAME,
#         "--author",
#         "author",
#         "--sep",
#         "--release",
#         "",
#         "--language",
#         "en",
#         "--ext-autodoc",
#         "--ext-githubpages",
#         "--extensions",
#         "myst_parser",
#         "--extensions",
#         "sphinx.ext.napoleon",
#         "--extensions",
#         "sphinx_copybutton",
#         external=True,
#     )


@nox.session(tags=["docs"])
def gen_docs(session: nox.Session) -> None:
    """Generate docs outputs."""
    if session.posargs:
        (version,) = session.posargs
    else:
        version = "latest"

    session.chdir("docs")

    # Clean up generated RST and HTML files
    session.run("rm", "-rf", "build", external=True)
    session.run(
        "rm", "-rf", f"source/api/{PYTHON_PROJECT_NAME}.rst", external=True
    )
    session.run("rm", "-rf", "source/api/modules.rst", external=True)

    # Generate API docs
    session.run(
        "sphinx-apidoc",
        "-o",
        "source/api",
        f"../{PYTHON_PROJECT_NAME}",
        # Exclude dirs (odd choice by sphinx:
        # all args after first one are "exclude pattern")
        f"../{PYTHON_PROJECT_NAME}/tests",
        external=True,
    )

    # Generate sphinx output
    session.run(
        "sphinx-build",
        "source",
        f"build/{PYTHON_PROJECT_NAME}/{version}",
        "-W",
        external=True,
    )

    # Redirect top level to latest
    session.run(
        "cp",
        "source/_static/redirect_index.html",
        f"build/{PYTHON_PROJECT_NAME}/index.html",
        external=True,
    )


@nox.session(tags=["docs"])
def debug_docs(session: nox.Session) -> None:
    """Run local server to debug doc outputs."""
    gen_docs(session)

    # NB: We're already in "docs" dir because of `gen_docs()`
    session.chdir("build")
    session.log(f"Local server: http://localhost:8000/{PYTHON_PROJECT_NAME}")
    session.run("python", "-m", "http.server")

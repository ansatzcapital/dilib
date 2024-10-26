"""Nox setup.

To run all linters, checkers, and tests:
    nox

To run all fixers:
    nox -t fix

By default, nox will set up venvs for each session. To use your current
env instead, add `--no-venv` to any command:
    nox --no-venv

By default, nox will recreate venvs for each session. To reuse your existing
env instead, add `--reuse`/`-r` to any command:
    nox --reuse

To run all static linters and checkers:
    nox -t static

To pick a particular session, e.g.:
    nox --list
    nox -s fix_ruff
    nox -s pytest -- -k test_name

To do an editable install into your current env:
    nox -s develop

See https://nox.thea.codes/en/stable/index.html for more.
"""

import sys

import nox
import nox.virtualenv

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


@nox.session(tags=["static", "typecheck"])
def mypy(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run("mypy", "dilib")


@nox.session(tags=["static", "typecheck"])
def pyright(session: nox.Session) -> None:
    # TODO: Remove once pyright >= 1.1.387 is available. See:
    #   - https://github.com/microsoft/pyright/issues/9296
    #   - https://docs.python.org/3/library/sys.html#sys.platform
    if sys.platform == "win32":
        session.install("pyright <= 1.1.385")

    if is_isolated_venv(session):
        session.install("-e", ".[test]")

    env = {"PYRIGHT_PYTHON_VERBOSE": "1"}
    # Enable for debugging
    if False:
        env["PYRIGHT_PYTHON_DEBUG"] = "1"

    session.run("pyright", "dilib", env=env)


@nox.session(tags=["test"])
def pytest(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run("pytest", "dilib", *session.posargs)


@nox.session(tags=["lint", "static"])
def ruff(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run("ruff", "format", "dilib", "--check")
    session.run("ruff", "check", "dilib")


@nox.session(tags=["fix"])
def fix_ruff(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run("ruff", "format", "dilib")
    session.run("ruff", "check", "dilib", "--fix")


@nox.session(venv_backend="none")
def develop(session: nox.Session) -> None:
    # We install using compatibility mode for VS Code
    # to pick up the installation correctly.
    # See https://setuptools.pypa.io/en/latest/userguide/development_mode.html#legacy-behavior.
    session.run(
        "pip",
        "install",
        "-e",
        ".[setup,test]",
        "--config-settings",
        "editable_mode=compat",
    )

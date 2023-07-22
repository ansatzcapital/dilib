"""Nox setup.

To run all linters, checkers, and tests:
    nox

To run all fixers:
    nox -t fix

By default, nox will set up venvs for each session. To use your current
env instead, add `--no-venv` to any command:
    nox --no-venv

To run all static linters and checkers:
    nox -t static

To pick a particular session, e.g.:
    nox --list
    nox -s fix_black
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
    nox.options.sessions = ["fix_black", "fix_ruff"]
else:
    nox.options.sessions = ["black", "mypy", "pyright", "pytest", "ruff"]


def is_isolated_venv(session: nox.Session) -> bool:
    """Indicates that the session is being run in an isolated env.

    I.e., the user has not set `--no-venv`.

    If the user uses their development (non-isolated) venv,
    then nox will (correctly) refuse to install packages, unless forced to.
    """
    return not isinstance(session.virtualenv, nox.virtualenv.PassthroughEnv)


@nox.session(tags=["lint", "static"])
def black(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run("black", "--check", "dilib")


@nox.session(tags=["fix"])
def fix_black(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run("black", "dilib")


@nox.session(tags=["static", "typecheck"])
def mypy(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run("mypy", "dilib")


@nox.session(tags=["static", "typecheck"])
def pyright(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run(
        "pyright",
        "dilib",
        env={"PYRIGHT_PYTHON_DEBUG": "1", "PYRIGHT_PYTHON_VERBOSE": "1"},
    )


@nox.session(tags=["test"])
def pytest(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run("pytest", "dilib", *session.posargs)


@nox.session(tags=["lint", "static"])
def ruff(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
    session.run("ruff", "check", "dilib")


@nox.session(tags=["fix"])
def fix_ruff(session: nox.Session) -> None:
    if is_isolated_venv(session):
        session.install("-e", ".[test]")
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

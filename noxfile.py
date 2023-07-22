import sys

import nox
import nox.virtualenv

if any(arg.startswith("fix") for arg in sys.argv):
    nox.options.sessions = ["fix_black", "fix_ruff"]
else:
    nox.options.sessions = ["black", "mypy", "pyright", "pytest", "ruff"]


def is_isolated_venv(session: nox.Session) -> bool:
    """Indicates that the user has set --no-venv.

    This means the user is using their development venv, and nox will (correctly) refuse to install packages unless
    forced to."""
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
    session.run("pyright", "dilib", env={"PYRIGHT_PYTHON_DEBUG": "1", "PYRIGHT_PYTHON_VERBOSE": "1"})


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
    # We install using compatibility mode for VS Code to pick up the installation correctly.
    # See https://setuptools.pypa.io/en/latest/userguide/development_mode.html#legacy-behavior.
    session.run("pip", "install", "-e", ".[setup,test]", "--config-settings", "editable_mode=compat")

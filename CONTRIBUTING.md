# Contributing

## Env

```bash
uv sync --extra all && . .venv/bin/activate
```

If you want to use different versions:

```bash
uv venv .venv_py312 --python 3.12 && . .venv_py312/bin/activate
```

You can also force set Python versions in Nox:

```bash
nox -P 3.12
```

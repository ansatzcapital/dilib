# Contributing

## Env

```bash
./scripts/act_dev.sh
```

Equivalently:

```bash
pixi shell -e dev
```

We recommend using [Pixi](https://pixi.sh/latest/) to be able to
easily run tests (including `test-matrix` across Python versions), but
you can also use [uv](https://docs.astral.sh/uv/) to set up your env:

```bash
uv sync --all-extras --group dev && . .venv/bin/activate

# Or to approximately mirror Pixi's method of starting a new shell:
uv sync --all-extras --group dev && bash --rcfile <(echo 'source ~/.bashrc; . .venv/bin/activate')
```

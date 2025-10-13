# dilib

Dependency injection (DI) library for Python

[![PyPI version](https://badge.fury.io/py/dilib.svg)](https://badge.fury.io/py/dilib)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/dilib.svg)](https://pypi.python.org/pypi/dilib/)
[![GitHub Actions (Tests)](https://github.com/ansatzcapital/dilib/workflows/Test/badge.svg)](https://github.com/ansatzcapital/dilib)

## Installation

`dilib` is available on [PyPI](https://pypi.org/project/dilib/):

```bash
pip install dilib
```

## Documentation

Documentation, design principles, and patterns are available [here](https://ansatzcapital.github.io/dilib).

Examples are available [here](https://github.com/ansatzcapital/dilib/tree/main/examples).

## About DI

[Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection)
can be thought of as a **software engineering pattern**
as well as a **framework**. The goal is to describe and instantiate objects
in a more composable, modular, and uniform way.

The **pattern** is: when creating objects, always express what you depend on,
and let someone else give you those dependencies. (This is sometimes
referred to as the "Hollywood principle": "Don't call us; we'll call you." 😎)

The **framework** is meant to ease the inevitable boilerplate
that occurs when following this pattern, and `dilib` is one such framework.
It makes it easier to describe a large graph of dependent objects
and then instantiate only the objects you need as you need them.

## Quick Start

The framework takes a 3-step approach to configuring and instantiating objects.
Think of it like [mise en place](https://en.wikipedia.org/wiki/Mise_en_place),
a method of cooking where you prepare everything in its place
before taking actions.

The 3 steps are:

1. 🥣 **Prepare:** Describe the recipe of how objects are to be created and how
they depend on each via **specs** inside **configs**
2. 🔄 **Replace:** Optionally, perturb the configs
3. 🔥 **Create:** Create the **container**, which lazily instantiates only the
objects needed per user request

These are the 3 major components needed for these 3 steps:

- **Specs**: These are the recipes that
describe how to instantiate the object when needed later. Common specs
include:
    - `dilib.Object(obj)`: Pass through precreated object (often used
    for primitive config values).
    - `dilib.Prototype(cls, *args, **kwargs)`: Whenever the container
    is asked to create this object, call `cls(*args, **kwargs)`
    each time (with no caching).
    - `dilib.Singleton(cls, *args, **kwargs)`: Same as `Prototype`,
    except the result is cached per config field per container.
    - `dilib.Forward(other_spec)`: Forward this request to another spec.
    Think of it like a [mux](https://en.wikipedia.org/wiki/Multiplexer)
    or control switch.
    - For more, see [Overview](https://ansatzcapital.github.io/dilib/latest/overview.html).
- `dilib.Config`: Configs give names to specs and also provide a
way to describe how the specs depend on each other. Configs can nest
and reference each other via **child configs**, defined in the same
syntax as specs. Configs can be arbitrarily perturbed programmatically.
- `dilib.Container`: This is the chef, i.e., the object retriever.
It's in charge of *materializing*/*instantiating* the aforementioned
delayed specs into actual instances and caching these objects when required,
(i.e., in the case of `dilib.Singleton`).

```python
from __future__ import annotations

import abc
import dataclasses

import dilib


# API
class Engine(abc.ABC):
    pass


# An implementation of the engine API that makes network calls
@dataclasses.dataclass(frozen=True)
class DBEngine(Engine):
    address: str
    token: str | None = None


# An implementation of the engine API designed for testing
class MockEngine(Engine):
     pass


# An object that depends on having an instance of an `Engine`
@dataclasses.dataclass(frozen=True)
class Car:
    # Takes an `Engine` instance via "constructor injection"
    engine: Engine


class EngineConfig(dilib.Config):
    # Glboal inputs are provided by the config **user**
    db_address = dilib.GlobalInput(str, default="some-db-address")

    # Local inputs are provided by downstream config **author**
    token_prefix = dilib.LocalInput(str)

    # Simple primitives must be wrapped in `Object`
    token_suffix = dilib.Object(".bar")

    # Because this lambda is wrapped in a `Prototype`, it will
    # only be called if required. Note how specs depend on other specs
    # explicitly via named aliases.
    token = dilib.Prototype(lambda x, y: x + y, x=token_prefix, y=token_suffix)

    # `Singleton` is very much like `Prototype`, except the container
    # will cache this instance by the key `db_engine0`
    db_engine0 = dilib.Singleton(DBEngine, db_address, token=token)

    # Alternate engine spec
    db_engine1 = dilib.Singleton(DBEngine, db_address)

    # Forward spec resolution to the target spec.
    # Note how we widen the type of the object from `DBEngine` to `Engine`.
    engine: Engine = dilib.Forward(db_engine0)


class CarConfig(dilib.Config):
    # Configs can depend on other configs. Here, `CarConfig`
    # depends on an `EngineConfig` (with local input value set).
    engine_config = EngineConfig(token_prefix="baz")

    # The idea is to reach into child configs and get whatever objects you
    # need from there
    car = dilib.Singleton(Car, engine_config.engine)


# Get instance of root config (with global input value set)
car_config = dilib.get_config(CarConfig, db_address="another-db-address")

# Perturb here as you'd like. Note that the new object
# doesn't need to have been set up by the config author beforehand.
car_config.engine_config.engine = dilib.Singleton(MockEngine)

# Create container from config
container = dilib.get_container(car_config)

# Retrieve objects from container (some of which are cached inside),
# all with IDE auto-complete and static type checking
assert container.config.engine_config.db_address == "another-db-address"
assert isinstance(container.config.engine_config.engine, MockEngine)
assert isinstance(container.config.car, Car)
assert container.config.car is container.car  # Because it's a Singleton
```

Notes:

- `Car` *takes in* an `Engine` via its constructor
(known as ["constructor injection"](https://en.wikipedia.org/wiki/Dependency_injection#Constructor_injection)),
instead of making or getting one within itself.
- For this to work, `Car` cannot make any assumptions about
*what kind* of `Engine` it received. Different engines have different
constructor params but have the [same API and semantics](https://en.wikipedia.org/wiki/Liskov_substitution_principle).
- Both config wiring and `container.config` calls are all statically
type safe, meaning you should see auto-complete in your IDE and
everything should pass `mypy` and `pyright` checking.

## Features

### Overview

* 📇 **Global addressability:** `dilib` provides a way to map a
unique name to an object instance. E.g., with Python, you can come up
with a fully-qualified name of a class or symbol
(just `module_a.module_b.SomeClass`), but there is no natural parallel
for object *instances* (without resorting to global variables).
* ⧴ **Delayed instantiation:** If you're describing a very large graph
of objects, it's useful to delay instantiation such that you create
only the exact subgraph of objects required to fulfill the user's request
on the container. It's especially important that these instantiations
(which can have expensive compute or IO calls) not be done at import time.
* 🔄 **Ability to perturb with self-consistency guarantee:** Delayed
instantiation also provides a guarantee of self-consistency. If two or more
objects depend on a parameter, and that parameter is perturbed, you almost
certainly want both objects to see only the new value. By having a linear
set of steps to take--create config, perturb config, create container
(which *freezes* the config from further perturbations automatically)--you
know that all instantiations are performed exactly
after all perturbations have been performed.
See [below](#perturb-config-fields-with-ease).
* 🛠️ **Static auto-complete and type safety**: All attrs available
on a `container.config`, as well as specs and child configs,
are available statically to both the IDE and
any standard type checker like `mypy` and `pyright`.
Equivalent dynamic attrs for IPython/Jupyter sessions are also available.
All calls to specs like `dilib.Singleton`
are annotated with `ParamSpec`s, so static type checkers should
alert you if you get arg names wrong or mismatches in types.
* 🚫🌎 **Discourages global state:** Often, implementations
of the [singleton pattern](https://en.wikipedia.org/wiki/Singleton_pattern)
come with the baggage of global state. However, with `dilib`
(and DI in general), the lifecycle of an object is managed by the
authors of the config/bindings, not by the downstream clients of the object.
Thus, we can achieve a singleton lifecycle
with respect to all the objects in the *container*, instead of
with respect to all the objects in the *process*.
* ⌨️ **Optionally easier syntax:** If you don't mind "polluting" your object
model with references to the DI framework, you can opt into the easier
syntax mode, writing `MockEngine()` instead of `dilib.Singleton(MockEngine)`.
See [Easier syntax](https://ansatzcapital.github.io/dilib/latest/patterns.html#easier-syntax).

### Perturb Config Fields with Ease

A major goal of `dilib` is the ability to perturb any config field
and have a guarantee that, when instantiated, all objects that depend on
that field will see the same perturbed value.

This enables the user to easily perform param scans, integration tests,
meta-optimizers, and more, even with params that are deeply
embedded in the system. Furthermore, these can be performed in the
same process, side-by-side. E.g.:

```python
def get_container(
    db_address: str = "db-address",
    perturb_func: Callable[[CarConfig], None] | None = None,
) -> dilib.Container[CarConfig]:
    """Helper for users to get container instance.

    This should only be called at the application level, never by
    a function in a library.
    """

    config = dilib.get_config(CarConfig, db_address=db_address)

    if perturb_func is not None:
        perturb_func(config)

    return dilib.get_container(config)


def perturb_func_a(config: CarConfig) -> None:
    config.engine_config.token = "a"


def perturb_func_b(config: CarConfig) -> None:
    config.engine_config.token = "b"


# Create multiple containers for each perturbation
container_a = get_container(perturb_func=perturb_func_a)
container_b = get_container(perturb_func=perturb_func_b)

# Get cars corresponding to each perturbation, all in the same process space.
# No matter what object we get from `container_a`, it will only have been
# created using objects that have seen `token = "a"` perturbation.
car_a = container_a.config.car
car_b = container_a.config.car
```

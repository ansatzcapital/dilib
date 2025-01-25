# dilib

Dependency injection (DI) library for python

[![PyPI version](https://badge.fury.io/py/dilib.svg)](https://badge.fury.io/py/dilib)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/dilib.svg)](https://pypi.python.org/pypi/dilib/)
[![GitHub Actions (Tests)](https://github.com/ansatzcapital/dilib/workflows/Test/badge.svg)](https://github.com/ansatzcapital/dilib)

## Installation

`dilib` is available on [PyPI](https://pypi.org/project/dilib/):

```bash
pip install dilib
```

## Quick Start

The framework takes a 3-step approach to configuring and instantiating objects.
Think of it like [mise en place](https://en.wikipedia.org/wiki/Mise_en_place),
a method of cooking where you prepare everything in its place
before taking actions.

The 3 steps are:

1. Describe the recipe of how objects are to be created and how
they depend on each via **specs**
2. Optionally, perturb the recipes
3. Create the **container**, which lazily instantiates only the
objects needed per user request

And these are the 3 major components needed for these 3 steps:

- **Spec** like `dilib.{Prototype,Singleton}`: These are the recipes that
describe how to instantiate the object when needed later.
See [API overview](#api-overview) below for details about these specs.
- `dilib.Config`: Configs give names to specs and also provide a
way to describe how the specs depend on each other. Configs can nest
and reference each other by setting child configs, defined with the same
syntax as specs. Configs can be arbitrarily perturbed programmatically.
- `dilib.Container`: This is the chef, i.e., the object retriever.
It's in charge of *materializing*/*instantiating* the aforementioned
 delayed specs that are wired together by config into actual instances
(plus caching, in the case of `dilib.Singleton`).

```python
from __future__ import annotations

import dataclasses
from typing import Optional

import dilib


# API
class Engine:
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
    db_address = dilib.GlobalInput(str, default="some-db-address")

    token_prefix = dilib.LocalInput(str)
    token = dilib.Prototype(lambda x: x + ".bar", x=token_prefix)

    # Objects depend on other objects via named aliases
    db_engine0 = dilib.Singleton(DBEngine, db_address, token=token)

    # Alternate engine spec
    db_engine1 = dilib.Singleton(DBEngine, db_address)

    # Forward spec resolution to the target spec.
    # Note how we widen the type of the object from `DBEngine` to `Engine`.
    engine: Engine = dilib.Forward(db_engine0)


class CarConfig(dilib.Config):
    # Configs can depend on other configs. Here, `CarConfig`
    # depends on an `EngineConfig` (with this particular param set).
    engine_config = EngineConfig(token_prefix="baz")

    car = dilib.Singleton(Car, engine_config.engine)


# Get instance of config (with global input value set)
car_config: CarConfig = dilib.get_config(
    CarConfig, db_address="another-db-address"
)

# Perturb here as you'd like. Note that the new object
# doesn't need to have been set up beforehand. E.g.:
car_config.engine_config.engine = dilib.Singleton(MockEngine)

# Pass config to a container
container: dilib.Container[CarConfig] = dilib.get_container(car_config)

# Retrieve objects from container (some of which are cached inside)
assert container.config.engine_config.db_address == "another-db-address"
assert isinstance(container.config.engine_config.engine, MockEngine)
assert isinstance(container.config.car, Car)
assert container.config.car is container.car  # Because it's a Singleton
```

Notes:

- `Car` *takes in* an `Engine` via its constructor
(known as "constructor injection"), instead of making or
getting one within itself.
- For this to work, `Car` cannot make any assumptions about
*what kind* of `Engine` it received. Different engines have different
constructor params but have the [same API and semantics](https://en.wikipedia.org/wiki/Liskov_substitution_principle).
- In order to take advantage of typing (e.g., `mypy`, PyCharm auto-complete),
use `dilib.get_config(...)` and `container.config`,
which are type-safe alternatives to `CarConfig().get(...)` and
direct `container` access. Note also how we set the `engine` config field type
to the base class `Engine`--this way, clients of the config are
abstracted away from which implementation is currently configured.

### API Overview

- `dilib.Config`: Inherit from this to specify your objects and params
- `config = dilib.get_config(ConfigClass, **global_inputs)`: Instantiate
config object
- `container = dilib.get_container(config)`: Instantiate container object
by passing in the config object
- `container.config.x_config.y_config.z`: Get the instantianted object
  - Alternatively: `container.x_config.y_config.z`
  - Or even: `container["x_config.y_config.z"]`

Specs:

- `dilib.Object`: Pass-through already-instantiated object
- `dilib.Forward`: Forward to a different config field
- `dilib.Prototype`: Instantiate a new object at each container retrieval
- `dilib.Singleton`: Instantiate and cache object at each container retrieval
- `dilib.Singleton{Tuple,List,Dict}`: Special helpers to ease
collections of specs. E.g.:

```python
import dataclasses

import dilib


@dataclasses.dataclass(frozen=True)
class ValuesWrapper:
    x: int
    y: int
    z: int = 3


class CollectionsConfig(dilib.Config):
    x: int = dilib.Object(1)
    y: int = dilib.Object(2)
    z: int = dilib.Object(3)

    xy_tuple = dilib.SingletonTuple(x, y)
    xy_list = dilib.SingletonList(x, y)
    xy_dict0 = dilib.SingletonDict(x=x, y=y)
    xy_dict1 = dilib.SingletonDict({"x": x, "y": y})
    xy_dict2 = dilib.SingletonDict({"x": x, "y": y}, z=z)

    # You can also build a partial kwargs dict that can be
    # re-used and combined downstream
    partial_kwargs = dilib.SingletonDict(x=x, y=y)
    values0 = dilib.Singleton(ValuesWrapper, __lazy_kwargs=partial_kwargs)
    values1 = dilib.Singleton(
        ValuesWrapper, z=4, __lazy_kwargs=partial_kwargs
    )


config = dilib.get_config(CollectionsConfig)
container = dilib.get_container(config)

assert container.config.xy_tuple == (1, 2)
assert container.config.xy_list == [1, 2]
assert container.config.xy_dict0 == {"x": 1, "y": 2}
assert container.config.xy_dict1 == {"x": 1, "y": 2}
assert container.config.xy_dict2 == {"x": 1, "y": 2, "z": 3}
```

## Features

### Overview

* **Global addressessibility:** `dilib` provides a way to map a
unique name to an object instance. E.g., with Python, you can come up
with a fully-qualified name of a class or symbol
(just `module_a.module_b.SomeClass`), but the only simple solution
is to use global variables (which lack other features of `dilib`).
* **Delayed instantiation:** If you're describing a very large graph
of objects, it's useful to delay instantiation such that you can create
only the exact subgraph of objects required to fulfill the user's request
on the container.
* **Ability to perturb with self-consistency guarantee:** Delayed
instantiation also provides a guarantee of self-consistency: if two or more
objects depend on a parameter, and that parameter is perturbed, you almost
certainly want both objects to see only the new value. By having a linear
set of steps to take--create config, perturb config, create container,
which freezes the config--you know that all instantiations are
performed exactly after all perturbations have been performed.
See [below](#perturb-config-fields-with-ease).
* **Static auto-complete and type-safety**: All attrs available
on a `container.config`, as well as specs and child configs,
are available statically to both the IDE and
any standard type checker like `mypy` and `pyright`
(i.e., it's not just available in an IPython session dynamically).
All calls to specs like `dilib.Singleton`
are annotated with `ParamSpec`s, so static type checkers should
alert you if you get arg names wrong or mismatches in types.
* **Discourages global state:** Often, implementations
of [singleton pattern](https://en.wikipedia.org/wiki/Singleton_pattern)
come with the baggage of global state. However, with `dilib`
(and DI in general), the lifecycle of an object is managed by the
authors of the config/bindings, not by the downstream clients of the object.
Thus, we can achieve a singleton lifecycle
with respect to all the objects in the container without any global state.
* **Optionally easier syntax:** If you don't mind "polluting" your object
model with references to the DI framework, you can opt into the easier
syntax, writing `MockEngine()` instead of `dilib.Singleton(MockEngine)`.
See [below](#easier-syntax).

### Perturb Config Fields with Ease

A major goal of `dilib` is the ability to perturb any config field
and have a guarantee that, when instantiated, all objects that depend on
that field will see the same perturbed value.

This guarantee of self-consistency is achieved by separating config
specification from object instantiation, allowing perturbation to safely occur
in between. Note that once a config object is passed into a container,
it is automatically frozen and further perturbations are no longer allowed.

This enables the user to easily perform param scans, integration tests,
and more, even with params that are deeply embedded in the system. E.g.:

```python
def get_container(
    db_address: str = "db-address",
    perturb_func: Callable[[CarConfig], None] | None = None,
) -> dilib.Container[CarConfig]:
    config = dilib.get_config(CarConfig, db_address=db_address)
    if perturb_func is not None:
        perturb_func(config)
    return dilib.get_container(config)


def perturb_func_a(config: CarConfig) -> None:
    config.engine_config.token = "a"


def perturb_func_b(config: CarConfig) -> None:
    config.engine_config.token = "b"


# Create multiple containers for each perturbation
ctr_a = get_container(perturb_func=perturb_func_a)
ctr_b = get_container(perturb_func=perturb_func_b)

# Get cars corresponding to each perturbation, all in the same process space.
# No matter what object we get from ctr_a, it will only have been
# created using objects that have seen token="a".
car_a = ctr_a.config.car
car_b = ctr_b.config.car
```

### Easier Syntax

Some users find it tedious and unintuitive to have to describe objects
via the explicit spec instance. E.g.:

```python
# In normal Python, you just create what you want:
engine = MockEngine()

# But in dilib, you have to wrap object instantiations in specs:
engine = dilib.Singleton(MockEngine)
```

So `dilib` provides a shortcut via `SingletonMixin` and `PrototypeMixin`.
Just subclass one of these in the class you're writing:

```python
class MockEngine(dilib.SingletonMixin, Engine):
    ...
```

And then you can use the easier syntax:

```python
with dilib.config_context():

    class EngineConfig(dilib.Config):
        mock_engine = MockEngine()
```

Be sure to use `dilib.config_context()` when creating the config class!

Two major downsides to this approach are: (1) you're polluting the object
model with references to a particular DI framework (ideally, you should
be able to switch DI frameworks without a single change to model code),
and (2) you're hard-wiring the spec type to the class, removing
a degree of freedom from the config author.


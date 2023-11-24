# dilib

Dependency injection (DI) library for python

[![PyPI version](https://badge.fury.io/py/dilib.svg)](https://badge.fury.io/py/dilib)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/dilib.svg)](https://pypi.python.org/pypi/dilib/)
[![GitHub Actions (Tests)](https://github.com/ansatzcapital/dilib/workflows/Test/badge.svg)](https://github.com/ansatzcapital/dilib)

## About DI

[Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection)
can be thought of as a **software engineering pattern**
as well as a **framework**. The goal is to develop objects in a more
composable and modular way.

The **pattern** is: when creating objects, always express what you depend on,
and let someone else give you those dependencies. (This is sometimes
referred to as the "Hollywood principle": "Don't call us; we'll call you.")

The **framework** is meant to ease the inevitable boilerplate
that occurs when following this pattern, and `dilib` is one such framework.

See the [Google Clean Code Talk about Dependency Injection](https://testing.googleblog.com/2008/11/clean-code-talks-dependency-injection.html).

## Installation

`dilib` is available on [PyPI](https://pypi.org/project/dilib/):

```bash
pip install dilib
```

## Quick Start

There are 3 major parts of this framework:

- `dilib.{Prototype,Singleton}`: A recipe that describes how to instantiate
the object when needed later. `dilib.Prototype` indicates to the retriever
that a new instance should be created per retrieval,
while `dilib.Singleton` indicates only 1 instance of the object
should exist. (Both spec types inherit from `dilib.Spec`.)
- `dilib.Config`: Nestable bag of types and values, bound by specs,
that can be loaded, perturbed, and saved.
- `dilib.Container`: The object retriever--it's in charge of
_materializing_ the aforementioned delayed specs that
are wired together by config into actual instances
(plus caching, if indicated by the spec).

```python
from typing import Optional

import dilib


# API
class Engine:
    pass


# An implementation of the engine API that makes network calls
class DBEngine(Engine):
    def __init__(self, addr: str, token: Optional[str] = None):
        self.addr = addr
        self.token = token


# An implementation of the engine API designed for testing
class MockEngine(Engine):
     pass


class Car:
    # Takes an Engine instance via constructor injection
    def __init__(self, engine: Engine):
        self.engine = engine


class EngineConfig(dilib.Config):
    db_addr = dilib.GlobalInput(str, default="some-db-addr")

    token_prefix = dilib.LocalInput(str)
    token = dilib.Prototype(lambda x: x + ".bar", x=token_prefix)

    # Objects depend on other objects via named aliases
    engine0: Engine = dilib.Singleton(DBEngine, db_addr, token=token)
    # Or equivalently, if DBEngine used dilib.SingletonMixin:
    # engine0 = dilib.DBEngine(db_addr, token=token)

    # Alternate engine spec
    engine1: Engine = dilib.Singleton(DBEngine, db_addr)

    # Forward spec resolution to the target spec
    engine: Engine = dilib.Forward(engine0)


class CarConfig(dilib.Config):
    # Configs depend on other configs via types.
    # Here, CarConfig depends on EngineConfig.
    engine_config = EngineConfig(token_prefix="baz")

    car = dilib.Singleton(Car, engine_config.engine)


# Get instance of config (with global input value set)
car_config: CarConfig = dilib.get_config(
  CarConfig, db_addr="some-other-db-addr"
)

# Perturb here as you'd like. E.g.:
car_config.engine_config.engine = dilib.Singleton(MockEngine)

# Pass config to a container
container: dilib.Container[CarConfig] = dilib.get_container(car_config)

# Retrieve objects from container (some of which are cached inside)
assert container.config.engine_config.db_addr == "some-other-db-addr"
assert isinstance(container.config.engine_config.engine, MockEngine)
assert isinstance(container.config.car, Car)
assert container.config.car is container.car  # Because it's a Singleton
```

Notes:
- `Car` *takes in* an `Engine` via its constructor
(known as "constructor injection"),
instead of making or getting one within itself.
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
  - Alternatively: `config = ConfigClass().get(**global_inputs)`
- `container = dilib.get_container(config)`: Instantiate container object
by passing in the config object
  - Alternatively: `container = dilib.Container(config)`
- `container.config.x_config.y_config.z`: Get the instantianted object
  - Alternatively: `container.x_config.y_config.z`,
or even `container["x_config.y_config.z"]`

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

## Comparisons with Other DI Frameworks

### pinject

A prominent DI library in
python is [`pinject`](https://github.com/google/pinject).

#### Advantages of dilib

- Focus on simplicity. E.g.:
  - `foo = dilib.Object("a")` rather than `bind("foo", to_instance="a")`.
  - Child configs look like just another field on the config.
- Getting is via *names* rather than *classes*.
  - In `pinject`, the equivalent of container attr access
    takes a class (like `Car`) rather than a config address.
- No implicit wiring: No assumptions are made about aligning
arg names with config params.
  - Granted, `pinject` does have an explicit mode,
    but the framework's default state is implicit.
  - The explicit wiring in dilib configs obviates the need
  for complications like [inject decorators](https://github.com/google/pinject#safety)
  and [annotations](https://github.com/google/pinject#annotations).
- Minimal or no pollution of objects: Objects are not aware of
the DI framework. The only exception is:
if you want the IDE autocompletion to work when wiring up configs in an
environment that does not support `ParamSpec`
(e.g., `car = Car(engine=...)`), you have
to inherit from, e.g., `dilib.SingletonMixin`. But this is completely
optional; in `pinject`, on the other hand, one is required to
decorate with `@pinject.inject()` in some circumstances.

### dependency-injector

Another prominent DI library in python is [`dependency-injector`](https://github.com/ets-labs/python-dependency-injector).

#### Advantages of dilib

- `dilib` discourages use of class-level state by not supporting it
(that is, `dilib.Container` is equivalent to
`dependency_injector.containers.DynamicContainer`)
- Cleaner separation between "config" and "container"
(dependency-injector conflates the two)
- Easy-to-use perturbing with simple `config.x = new_value` syntax
- Easier to nest configs via config locator pattern
- Child configs are typed instead of relying on
`DependenciesContainer` stub (which aids in IDE auto-complete)
- Easier-to-use global input configuration
- Written in native python for more transparency

## Design

### Prevent Pollution of Objects

The dependency between the DI config and the actual objects in the
object graph should be one way:
the DI config depends on the object graph types and values.
This keeps the objects clean of
particular decisions made by the DI framework.

(`dilib` offers optional mixins that violate this decision
for users that want to favor the typing and
auto-completion benefits of using the object types directly.)

### Child Configs are Singletons by Type

In `dilib`, when you set a child config on a config object,
you're not actually instantiating the child config.
Rather, you're creating a spec that will be instantiated
when the root config's `.get()` is called.
This means that the config instances are singletons by type
(unlike the actual objects specified in the config, which are by alias).
It would be cleaner to create instances of common configs and
pass them through to other configs
(that's what DI is all about, after all!). However, the decision was made
to not allow this because this would make
building up configs almost as complicated as building up the
actual object graph users are interested in
(essentially, the user would be engaged in an abstract meta-DI problem).
As such, all references to the same config type are
automatically resolved to the same instance,
at the expense of some flexibility and directness.
The upside, however, is that it's much easier to create nested configs,
which means users can get to designing the actual object graph quicker.

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
    db_addr: str = "db-addr",
    perturb_func: Callable[[CarConfig], None] | None = None,
) -> dilib.Container[CarConfig]:
    config = dilib.get_config(CarConfig, db_addr=db_addr)
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

### Factories for Dynamic Objects

If you need to configure objects dynamically
(e.g., check db value to resolve what type to use,
set config keys based on another value), consider a factory pattern like:

```python
import dataclasses

import dilib


# Object that needs to be created dynamically
@dataclasses.dataclass(frozen=True)
class Foo:
    value: int


# Factory that takes static params via constructor injection and
# dynamic params via method injection
@dataclasses.dataclass(frozen=True)
class FooFactory:
    db_host: str
    alpha: int
    beta: int

    def get_foo(self, gamma: int) -> Foo:
        raise NotImplementedError


# Object that needs Foo object
@dataclasses.dataclass(frozen=True)
class FooClient:
    foo_factory: FooFactory

    def process_foo_value(self) -> int:
        return 100 + self.foo_factory.get_foo(gamma=3).value


class FooConfig(dilib.Config):
    db_host = dilib.GlobalInput(type_=str, default="some-db-addr")
    foo_factory = dilib.Singleton(
        FooFactory, db_host=db_host, alpha=1, beta=2
    )
    foo_client = dilib.Singleton(FooClient, foo_factory=foo_factory)
```

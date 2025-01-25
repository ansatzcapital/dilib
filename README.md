# dilib

Dependency injection (DI) library for python

[![PyPI version](https://badge.fury.io/py/dilib.svg)](https://badge.fury.io/py/dilib)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/dilib.svg)](https://pypi.python.org/pypi/dilib/)
[![GitHub Actions (Tests)](https://github.com/ansatzcapital/dilib/workflows/Test/badge.svg)](https://github.com/ansatzcapital/dilib)

## About DI

[Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection)
can be thought of as a **software engineering pattern**
as well as a **framework**. The goal is to describe and instantiate objects in a more
composable, modular, and uniform way.

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
    db_host = dilib.GlobalInput(type_=str, default="some-db-address")
    foo_factory = dilib.Singleton(
        FooFactory, db_host=db_host, alpha=1, beta=2
    )
    foo_client = dilib.Singleton(FooClient, foo_factory=foo_factory)
```

## Comparisons with Alternatives

### Non-DI Alternatives

`dict[str, Any]`

```python
# Engine config/container
container["address"] = "some-db-address"
container["db_engine"] = DBEngine(container["address"])
container["mock_engine"] = MockEngine()
container["engine"] = container["engine_config"]["alt_engine"]

# Car config/container
container = {"engine_config": container}
container["car_a"] = Car(container["engine_config"]["engine"])
```

`TypedDict`

```python
class EngineConfig(TypedDict):
    address: str
    db_engine: DBEngine
    mock_engine: MockEngine
    engine: Engine


class CarConfig(TypedDict):
    engine_config: EngineConfig
    car: Car


address = "some-db-address"
db_engine = DBEngine(address)
engine = db_engine
engine_config = EngineConfig({
    address: address,
    db_engine: db_engine,
    mock_engine: MockEngine(),
    engine: engine,
})
car_config = CarConfig({
    "engine_config": engine_config,
    "car": Car(engine_config["engine"]),
})
```

Text config (e.g., YAML)

```yaml
engine_config:
    address: &address "some-db-address"
    db_engine: &engine
        class: "module_a.DBEngine"
        address: *address
    mock_engine:
        class: "module_b.MockEngine"
    engine: *engine
car_config:
    car: "module_c.Car"
    engine: *engine
```

Or one could handle references in Python code instead:

```yaml
engine_config:
    address: "some-db-address"
    db_engine:
        class: "module_a.DBEngine"
        address: "ref:..address"
    mock_engine:
        class: "module_b.MockEngine"
    engine: "ref:db_engine"
car_config:
    car: "module_c.Car"
    engine: "ref:..engine_config.engine"
```

`dataclasses`

```python
@dataclasses.dataclass(frozen=True)
class EngineConfig:
    address: str
    db_engine: DBEngine
    mock_engine: MockEngine
    engine: Engine


@dataclasses.dataclass(frozen=True)
class CarConfig:
    engine_config: EngineConfig
    car: Car


# Essentially identical to `TypedDict` above
```

Global variables

```python
address = "some-db-address"
DB_ENGINE = DBEngine(address)
MOCK_ENGINE = MockEngine()
ENGINE = DB_ENGINE

CAR = Car(ENGINE)
```

### Comparison with Non-DI Alternatives

|Method|Global addressessibility|Static auto-complete & type-safety|Delayed instantation|Self-consistent perturb|
|-|-|-|-|-|
|`dict[str, Any]`|✅*|❌|❌|❌|
|`TypedDict`|✅*|✅|❌|❌|
|Text config (e.g., YAML)|✅|❌|✅|✅|
|`dataclasses`|✅*|✅|❌|❌|
|Global variables|✅**|✅|❌|❌|
|`dilib`|✅|✅|✅|✅|

*One would need a simple helper that recurses down attrs one level at a time.
E.g., something that would translate `"engine_config.engine"` to getting attr
`"engine_config"` first, followed by `"engine"`.
**Native Python fully-qualified name

### DI Alternatives

#### pinject

Advantages of `dilib` over [`pinject`](https://github.com/google/pinject):

- It has been archived by the owner on Jan 10, 2023
- Focus on simplicity. E.g.:
  - `foo = dilib.Object("a")` rather than `bind("foo", to_instance="a")`.
  - Child configs look like just another field on the config.
- Getting is via *names* rather than *classes*.
  - In `pinject`, the equivalent of container attr access
    takes a class (like `Car`) rather than a config addressess.
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

#### dependency-injector

Advantages of `dilib` over [`dependency-injector`](https://github.com/ets-labs/python-dependency-injector):

- `dilib` highly encourages static containers over dynamic ones
by not including dynamic functionality at all
- Cleaner separation between "config" and "container"
(`dependency-injector` conflates the two)
- Easy-to-use perturbing with simple `config.x = new_value` syntax
- Easier to nest configs, with same syntax as defining specs
- Child configs are strongly typed instead of relying on
`DependenciesContainer` stub
(which enables IDE auto-complete and type checking)
- No separation between configuration and specs: they have the same
syntax and static typing capability
- Easier-to-use global input configuration
- Written in native python for more transparency

## Design Principles

### Static Typing

A large constraint of the design of this framework was that the both
config authors and container users should be able to statically reason
about the objects and values they're using. That is, it's important
that all `dilib` functionality is compatible with `mypy` and `pyright`
type checking, with no magic or plugins required.

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

## Tips, Patterns, and FAQs

### When should I use type annotations?

TODO

### Why do I need to wrap object instantions in specs?

TODO

### What's the deal with `container.config` and config types?

TODO

### Anti-pattern: use of container inside of library code

TODO


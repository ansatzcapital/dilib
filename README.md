# dilib

Dependency injection (DI) library

[![PyPI version](https://badge.fury.io/py/dilib.svg)](https://badge.fury.io/py/dilib)
[![PyPI Supported Python Versions](https://img.shields.io/pypi/pyversions/dilib.svg)](https://pypi.python.org/pypi/dilib/)
[![GitHub Actions (Tests)](https://github.com/ansatzcapital/dilib/workflows/Test/badge.svg)](https://github.com/ansatzcapital/dilib)

## About DI

[Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection) is a philosophy of building objects in a modular and composable way.

The philosophy is: when creating objects, always express what you depend on, and let someone else give you those dependencies.

The framework is code to ease the inevitable boilerplate that occurs when following this philosophy.

## Quick Start

There are 3 major parts of this framework:
- `dilib.Spec`: Describes what should be called or instantiated later.
- `dilib.Config`: Nestable bag of params (types and values) that can be loaded, perturbed, and subsequently frozen.
- `dilib.Container`: In charge of materializing delayed specs that are wired together by config into actual instances (plus caching).

(There are also mixins that provide convenient ways to enable the use of IDE auto-completion when writing configs.)

```python
import dilib


class Engine:
    pass


class DBEngine(Engine):

    def __init__(self, addr: str, user: str):
        self.addr = addr
        self.user = user


class MockEngine(Engine):
     pass


class Car:

    def __init__(self, engine: Engine):
        self.engine = engine


# noinspection PyTypeChecker
class EngineConfig(dilib.Config):

    db_addr = dilib.GlobalInput(str, "some-db-addr")
    db_user = dilib.LocalInput(str)
    adj_db_user = dilib.Prototype(lambda x: x + ".foo", x=db_user)

    engine = dilib.Singleton(DBEngine, db_addr, user=adj_db_user)
    # Or equivalently, if DBEngine used SingletonMixin:
    # engine = dilib.DBEngine(db_addr, user=adj_db_user)


class CarConfig(dilib.Config):

    # CarConfig depends on EngineConfig
    engine_config = EngineConfig(db_user="user")

    car = Car(engine_config.engine)


# Get instance of config (with global input value set)
car_config = CarConfig().get(db_addr="some-other-db-addr")

# Perturb here as you'd like. E.g.:
car_config.engine_config.Engine = MockEngine()

# Pass config to a container that can get and cache objs for you
container = dilib.Container(car_config)

assert container.engine_config.db_addr == "some-other-db-addr"
assert isinstance(container.car, Car)
assert container.car is container.car  # Because it's a Singleton
```

Notes:
- `Car` *takes in* an `Engine` instead of making or getting one within itself.
- For this to work, `Car` cannot make any assumptions about *what kind* of `Engine` it received.
Different engines have different constructor params but have the same API and semantics.

## Compare with Other DI Frameworks

### pinject

A prominent DI library in python is [pinject](https://github.com/google/pinject). See [this snippet](http://ava-gitlabl001.psd.r53/snippets/23) for an example.

#### Advantages of dilib
- Focus on simplicity. E.g.:
  - `foo = "a"` rather than `bind("foo", to_instance="a")`.
  - Child configs look like just another field on the config.
- Getting is via *names* rather than *classes*.
  - In pinject, the equivalent of `ctr.__getattr__()` takes a class (like `Car`) rather than a config address.
- No implicit wiring: No assumptions are made about aligning arg names with config params.
  - Granted, pinject does have an explicit mode, but the framework's default state is implicit.
  - The explicit wiring in dilib configs obviates the need for complications like [inject decorators](https://github.com/google/pinject#safety) and [annotations](https://github.com/google/pinject#annotations).
- Minimal or no pollution of objects: Objects are not aware of the DI framework. The only exception is
if you want the IDE autocompletion to work in configs (e.g., `car = Car(engine=...)`), you have
to inherit from, e.g., `dilib.SingletonMixin`, but this is completely optional. 
In pinject, on the other hand, one is required to decorate with `@pinject.inject()` in some circumstances.

### dependency-injector

Another prominent DI library in python is [dependency-injector](https://github.com/ets-labs/python-dependency-injector).

#### Advantages of dilib
- dilib discourages use of class-level state by not supporting it (that is, `dilib.Container` is equivalent to `dependency_injector.containers.DynamicContainer`).
- Cleaner separation between "config" and "container" (dependency-injector conflates the two).
- Easy-to-use perturbing with simple `config.x = new_value` syntax.
- Easier to nest configs via config locator pattern.
- Child configs are typed instead of relying on `DependenciesContainer` stub (which aids in IDE auto-complete).
- Easier-to-use global input configuration.
- Written in Python for more transparency (as opposed to Cython).

## Design

### Prevent Pollution of Objects

The dependency between the DI config and the actual objects in the object graph should be one way: the DI config depends on the object graph types and values. This keeps the objects clean of particular decisions made by the DI framework.

(`dilib` offers optional mixins that violate this decision for users that want to favor the typing and auto-completion benefits of using the object types directly.)

### Child Configs are Singletons by Type

In `dilib`, when you set a child config on a config object, you're not actually instantiating the child config. Rather, you're creating a spec that will be instantiated when the root config's `.get()` is called. This means that the config instances are singletons by type (unlike the actual objects specified in the config, which are by alias). It would be cleaner to create instances of common configs and pass them through to other configs (that's what DI is all about!). However, the decision was made to not allow this because this would make building up configs almost as complicated as building up the actual object graph users are interested in (essentially, the user would be engaged in an abstract meta-DI problem). As such, all references to the same config type are automatically resolved to the same instance, at the expense of some flexibility and directness. The upside, however, is that it's much easier to create nested configs, which means users can get to designing the actual object graph quicker.

### Factories for Dynamic Objects

If you need to configure objects dynamically (e.g., check db value to resolve what type to use, set config keys based on another value), consider a factory pattern like:

```python
class FooConfig(dilib.Config):
    db_param = dilib.Object("somedb")
    foo_factory = dilib.Singleton(FooFactory, db_param)
    foo_client = dilib.Singleton(FooClient, foo_factory=foo_factory)
```

# Patterns

## Why do I need to wrap object instantions in specs?

Ideally, the config/container user only ever has to instantiate the set
of objects they exactly need when calling `container.config.x`.
Even if you follow the generally good practice of not doing a lot of
work in constructors with the classes you write, it's possible you
don't have control over all the classes you're wiring up.

So *specs* provide a recipe of how objects should be created when
they're eventually retrieved, without instantiating them until they're needed.

## Easier syntax

Some users find it tedious and unintuitive to have to describe objects
via the spec syntax. E.g.:

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

## Forwarding pattern

Sometimes you have different implementations of the same
abstract base class, and you want to make it easy to switch between
the implementations. (You can think of it like a [multiplexer
pattern](https://en.wikipedia.org/wiki/Multiplexer).) In this case,
you can use `dilib.Forward`:

```python
class Engine:
    pass


class SomeEngine(Engine):
    pass


class AnotherEngine(Engine):
    pass


@dataclasses.dataclass(frozen=True)
class Car:
    # Note how this depends on the abstract base class `Engine`
    engine: Engine


class FooConfig(dilib.Config):
    some_engine = dilib.Singleton(SomeEngine)
    another_engine = dilib.Singleton(AnotherEngine)

    engine: Engine = dilib.Forward(some_engine)

    car = dilib.Singleton(Car, engine)
```

Then the config user can easily switch to another implementation
in a perturb function:

```python
config = dilib.get_config(FooConfig)

config.engine = dilib.Forward(config.another_engine)

container = dilib.get_container(config)

assert isinstance(container.config.engine, AnotherEngine)
```

## How do I perturb values and objects?

```{include} ../../README.md
:parser: myst_parser.sphinx_
:start-after: Perturb Config Fields with Ease
```

## When should I use type annotations?

Config fields automatically inherit correct types
based on the spec return type, so it's not required to set explicitly. E.g.:

```python
class FooConfig(dilib.Config):
    x = dilib.Object(1)
```

Hovering over `x` or `container.config.x` or using [`reveal_type`](https://docs.python.org/3/library/typing.html#typing.reveal_type)
should reveal `x: int`. (This works with all spec types, including
`Singleton`.)

The only time it's good to set types explicitly is when you want
to *widen* the type of a config field. E.g., you may want the
config field to be associated with an abstract base class instead
of the particular implementation class it's currently configured to.

This also helps with type checkers when you perturb the config
from one implementation to another.

For an example of how this ties into `dilib.Forward`, see [forwarding pattern](#forwarding-pattern).

## Factories for dynamic objects

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

## What's the deal with `container.config` and config types?

Originally, there were 2 (equivalent) ways to retrieve object instances
from the container:

1. `container.x.y.z`
2. `container["x.y.z"]`

But when we added type safety to `dilib`, we ran into an issue:
there's no way to specify a "proxy" or "deref" type hint*. That is, you
can't tell Python typing that `dilib.Container[T]` contains
all the attributes of `T` plus its own (e.g., `clear()`).

To get around this, we added a property called `config`
that's `cast` to `T`, and it simply forwards the attribute
call to the container.

Why choose the word `config` for this property? One can imagine
separating current config classes into 2: config APIs/protocols and particular
config mappings/bindings. In some ways, this would be a cleaner approach,
but it would also be very burdensome for the config author, so we
combine them into 1. However, if we didn't, one could imagine that this
`config` property would return the former config API/protocol type, hence
the name.

So now there are 3 ways to retrieve objects from containers:

1. `container.x.y.z`
2. `container["x.y.z"]`
3. `container.config.x.y.z`

(1) is nice in IPython and Jupyter sessions because you don't need
static typing in REPL; (2) is useful when asking the user for input
in a CLI app to perform functionality generic over many config fields;
and (3) is useful in all other contexts because it works with IDE
auto-complete and static type checkers like `mypy` and `pyright`.

*For further discussions about Python proxy/deref type hinting, see:
* [https://github.com/python/typing/issues/802](https://github.com/python/typing/issues/802)
* [https://github.com/python/typing/discussions/1560](https://github.com/python/typing/discussions/1560)
    * Interestingly, this discussion references Rust's [`Deref`](https://doc.rust-lang.org/std/ops/trait.Deref.html)
    as an example of functionality Python could adopt.

## Anti-pattern: use of container inside of library code

In general, containers should be created at the application level.
The idea is that containers hold the universe of objects being modeled,
giving the container user control over what's being created.

Creating containers inside library code breaks that paradigm
because the application level no longer has the ability to configure
the system as it desires.

In addition, it means that the overlapping objects in multiple containers
don't have references to the same objects, potentially causing
performance issues.

Finally, it breaks the idea that objects shouldn't know anything
about the DI framework in which they're created.

## Compare two systems in one process

The disadvantage of using global caches is that the process becomes
the container for all objects, making it difficult to test two
configurations of the same system with confidence.

With `dilib` containers, however, one can create multiple views
of objects that are isolated from each other in the same process (assuming
the objects being created don't access global state underneath). E.g.:

```python
default_config = dilib.get_config(CarConfig)
default_container = dilib.get_container(default_config)
default_car = default_container.config.car

alt_config = dilib.get_config(CarConfig)
alt_config.engine_config.db_address = "some-other-db"
alt_container = dilib.get_container(default_config)
alt_car = alt_container.config.car

# Now you have two handles to two different cars created from
# two independent sets of params
```

## Anonymous inner specs

When you want to delay the instantiation of an object, but it's only
ever used in a single parent spec and you don't need to perturb
this value, you can use anonymous inner specs like:

```python
class CarConfig(dilib.Config):
    car = dilib.Singleton(
        Car,
        engine=dilib.Singleton(DBEngine, address="some-db-address"),
    )
```

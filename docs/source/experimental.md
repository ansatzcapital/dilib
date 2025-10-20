# Experimental

New alternate syntax that's less DSL and more "regular Python classes",
inspired by writing the docs for "custom containers" in {doc}`non_lib_alts`

## Example

```python
import abc
import dataclasses
import enum
from typing import override

from dilib.experimental import Container, container, cache, call


#####################################################################
# Model Layer
#####################################################################


class Engine(abc.ABC):
    @abc.abstractmethod
    def start_engine(self) -> None: ...


@dataclasses.dataclass(frozen=True)
class MockEngine(Engine):
    @override
    def start_engine(self) -> None:
        print("Start mock engine")


@dataclasses.dataclass(frozen=True)
class DatabaseEngine(Engine):
    host: str
    port: int
    extra_param: int

    @override
    def start_engine(self) -> None:
        print("Start db engine:", self.host, self.port)


class TireType(enum.StrEnum):
    REGULAR = enum.auto()
    SPORT = enum.auto()
    SNOW = enum.auto()


@dataclasses.dataclass(frozen=True)
class Wheel:
    tire_type: TireType


class Car(abc.ABC):
    @abc.abstractmethod
    def start_car(self) -> None: ...


@dataclasses.dataclass(frozen=True)
class DefaultCar(Car):
    engine: Engine
    wheel0: Wheel
    wheel1: Wheel
    wheel2: Wheel
    wheel3: Wheel

    @override
    def start_car(self) -> None:
        self.engine.start_engine()


#####################################################################
# Config/Container Layer
#####################################################################


@container
class CommonContainer(Container):
    @call
    def env(self) -> str:
        return "dev"


@container
class EngineContainer(Container):
    common_ctr: CommonContainer
    input_host: str

    @call
    def host(self) -> str:
        return self.input_host

    @call
    def port(self) -> int:
        return 1234

    @call
    def extra_param(self) -> int:
        return 123

    @cache
    def engine(self) -> Engine:
        return DatabaseEngine(
            self.host, self.port, extra_param=self.extra_param
        )


@container
class WheelContainer(Container):
    common_ctr: CommonContainer
    input_tire_type: TireType = TireType.REGULAR

    @call
    def tire_type(self) -> TireType:
        return self.input_tire_type

    @call
    def wheel(self) -> Wheel:
        return Wheel(self.input_tire_type)


@container
class CarContainer(Container):
    common_ctr: CommonContainer
    engine_ctr: EngineContainer
    wheel_ctr: WheelContainer

    @cache
    def car(self) -> Car:
        return DefaultCar(
            engine=self.engine_ctr.engine,
            wheel0=self.wheel_ctr.wheel,
            wheel1=self.wheel_ctr.wheel,
            wheel2=self.wheel_ctr.wheel,
            wheel3=self.wheel_ctr.wheel,
        )


#####################################################################
# Application Layer
#####################################################################


def main() -> None:
    ctr = CarContainer.create({EngineContainer: {"input_host": "abc"}})

    car = ctr.car
    assert ctr.car is ctr.car

    engine = ctr.engine_ctr.engine
    assert car.engine is engine
    assert engine.host == "abc"
```

## Anatomy of a Container

A container is now a regular `dataclasses.dataclass(frozen=False, ...)`
with these types of values:

|Type|Examples from Above|Created|
|-|-|-|
|Field value|`EngineContainer.input_host`, `WheelContainer.input_tire_type`|Upon container creation (each container is created *once* per container type)|
|`@call` property value|`EngineContainer.host`, `WheelContainer.tire_type`, `WheelContainer.wheel`|Upon *every* value retrieval|
|`@cache` property value|`CarContainer.car`, `EngineContainer.engine`|Upon *first* value retrieval|

## Pros/Cons over Classic Syntax

Pros

- Classic syntax is in some ways a DSL, and this syntax is
basically just a plain Python class with cached properties
- Fewer concepts and easier-to-understand names (e.g., no separation
between configs and containers, no exposed singleton/prototype/etc. specs,
no special collection specs, no mix-in hacks, no lazy kwargs,
words like `cache` instead of `Singleton`, anonymous specs are expressed
with regular Python construction)
- Although classic syntax should work entirely with static type checkers,
because we don't need to "lie" to the type checker
(e.g., `dilib.Singleton(T) -> T`), we should have much more robust
static checking across editor/checker contexts and time
- Instead of a bag of global inputs (which can even collide),
local inputs are explicitly linked to their types,
but still easily available at the top level when creating a container
- Force user to consider when the container value type should be
abstract instead of concrete

Cons

- More boilerplate code. Specifically, everything needs to be a proper
Python property-style method (e.g., need to type `def ...`, can't infer
value type)

## Pros over Simple Alternative

Why not just have a container like this?

```python
@dataclasses.dataclass(frozen=True)
class FooContainer:
    bar_ctr: BarContainer

    @functools.cached_property
    def host(self) -> str:
        return "abc"

    @functools.cached_property
    def engine(self) -> Engine:
        return DatabaseEngine(self.host)
```

Because with `dilib`:

- Child containers get created automatically and also once per type
(i.e., there's only ever exactly one instance of `CommonContainer`
in every parent container in which it's referenced).
We assume this is what you probably want to do. It's all the more
difficult when the number of containers increase, with overlapping
common container instances that need to be cached across parent containers.
- Containers understand the hierarchy of parent/child containers
and support dotted keys (e.g., `ctr["x.y.z"]`), which means
every object now has a globally-addressable name
("global" with respect to the root config)
    - E.g., in CLIs with flags, you can have flags like `--name bar_ctr.xyz`
    that you pass to the root container directly
    (`ctr[args.name]`)
- We maintain self-consistency guarantee under perturbing because
we don't allow users to perturb after *any* object in the container
hierarchy has retrieved a value

## New Potential Pattern: Load Config from File

If some of your config values come from a config file (e.g., JSON, YAML, TOML),
you can use those values easily in the container:

```python
import json
from pathlib import Path

import cattrs
from dilib.experimental import Container, container


def load_config(value: T | str | Path, cls: type[T]) -> T:
    if isinstance(value, (str, Path)):
        converter = cattrs.Converter()
        data = json.load(Path(value).open("rb"))
        return converter.structure(data, cls)

    return value


@dataclasses.dataclass(frozen=True)
class EngineConfig:
    host: str
    port: int


@container
class EngineContainer(Container):
    input_config: EngineConfig | Path

    @cache
    def config(self) -> EngineConfig:
        return load_config(self.input_config)

    @cache
    def extra_param(self) -> int:
        return 123

    @cache
    def engine(self) -> Engine:
        return DatabaseEngine(
            self.host, self.port, extra_param=self.extra_param
        )


ctr0 = FooContainer.create(
    {EngineContainer: {"input_config": Path("config.json")}}
)
ctr1 = FooContainer.create(
    {EngineContainer: {"input_config": EngineConfig("abc", 8000)}}
)
```

Note that, for now, if you want to perturb `ctr.config`, you'll have to provide
the entire object, but you also can't perturb a container after getting a
value from it (it's frozen on first get to guarantee self-consistency).
(Perhaps we should add a `set_with(func: Callable[[T], T])` method?)

## Notes

- Primitives and cheap-to-construct objects should be decorated with
`@call`, while complex, expensive-to-construct objects should probably be
decorated with `@cache`.
- We no longer validate container params (the equivalent to global/local
inputs in classic). If the user wants this, they can validate
with a custom `__post_init__()` in their container class.
(Our type validation logic was never advanced enough to understand complex
types anyway.)


from __future__ import annotations

import abc
import dataclasses
import enum
from typing import Any

import pytest
from typing_extensions import override

from dilib.experimental import (
    Container,
    FrozenContainerError,
    cache,
    call,
    container,
)


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


class TireType(enum.Enum):
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

    @call
    def car(self) -> Car:
        return DefaultCar(
            engine=self.engine_ctr.engine,
            wheel0=self.wheel_ctr.wheel,
            wheel1=self.wheel_ctr.wheel,
            wheel2=self.wheel_ctr.wheel,
            wheel3=self.wheel_ctr.wheel,
        )


def test_basic() -> None:
    # Create container with the minimal number of required params
    # (in this case, `EngineContainer` requires an `input_host`).
    ctr = CarContainer.create({EngineContainer: {"input_host": "abc"}})

    # Child containers are cached by type.
    assert ctr.common_ctr is ctr.engine_ctr.common_ctr
    assert ctr.common_ctr is ctr.wheel_ctr.common_ctr

    # Get objects and check types.
    engine = ctr.engine_ctr.engine
    assert isinstance(engine, DatabaseEngine)
    car = ctr.car
    assert isinstance(car, DefaultCar)

    # Check that all the attributes are as expected.
    # Note that all values decorated with `@cache` (i.e., they're
    # singletons) are the same instance throughout, but all values
    # decorated with `@call` (i.e., they're prototypes)
    # get created on every call.
    assert engine is car.engine
    assert (
        car.wheel0.tire_type == TireType.REGULAR
        and car.wheel1.tire_type == TireType.REGULAR
        and car.wheel2.tire_type == TireType.REGULAR
        and car.wheel3.tire_type == TireType.REGULAR
    )
    assert car.wheel0 is not car.wheel1
    assert car.wheel0 is not car.wheel2
    assert car.wheel0 is not car.wheel3
    assert car.wheel0 is not ctr.wheel_ctr.wheel

    # We can't perturb the container once we've retrieved a value from it.
    with pytest.raises(FrozenContainerError):
        ctr.wheel_ctr.tire_type = TireType.SPORT


def test_typing() -> None:
    # We explicitly set types to show that the type checker understands
    # everything.
    ctr: CarContainer = CarContainer.create(
        {EngineContainer: {"input_host": "abc"}}
    )

    _0: CommonContainer = ctr.common_ctr
    _1: EngineContainer = ctr.engine_ctr
    _2: WheelContainer = ctr.wheel_ctr

    _3: Car = ctr.car
    _4: Engine = ctr.engine_ctr.engine
    _5: Wheel = ctr.wheel_ctr.wheel

    _6: str = ctr.engine_ctr.input_host


def test_dict_like() -> None:
    ctr = CarContainer.create({EngineContainer: {"input_host": "abc"}})

    # Get via dict-like syntax, but with dotted keys.
    assert "engine_ctr.engine" in ctr
    engine = ctr["engine_ctr.engine"]
    assert isinstance(engine, DatabaseEngine)

    # Check what happens with non-existent keys.
    assert "engine_ctr.foo" not in ctr
    with pytest.raises(KeyError):
        ctr["foo"]
    with pytest.raises(KeyError):
        ctr["engine_ctr.foo"]

    # Check that we can't perturb via dotted keys either.
    with pytest.raises(FrozenContainerError):
        ctr["engine_ctr.engine"] = MockEngine()

    # Check keys are the top-level values.
    assert ctr.keys() == {"common_ctr", "engine_ctr", "wheel_ctr", "car"}
    assert ctr.engine_ctr.keys() == {
        "common_ctr",
        "host",
        "port",
        "extra_param",
        "engine",
        # This arguably shouldn't show up here because it's not a
        # perturb-able value.
        "input_host",
    }


def test_ctr_params() -> None:
    # Check that our container params made their way through as expected.
    ctr = CarContainer.create(
        {
            EngineContainer: {"input_host": "abc"},
            WheelContainer: {"input_tire_type": TireType.SNOW},
        }
    )

    engine = ctr.engine_ctr.engine
    assert isinstance(engine, DatabaseEngine)
    car = ctr.car
    assert isinstance(car, DefaultCar)

    assert engine.host == "abc"
    assert car.wheel0.tire_type == TireType.SNOW

    # We should raise an error because we're missing the required
    # `EngineContainer` `input_host` param.
    with pytest.raises(TypeError):
        ctr = CarContainer.create(
            {WheelContainer: {"tire_type": TireType.SNOW}}
        )

    # We should raise an error because we have a typo and thought the
    # param was `tire_type` instead of the correct `input_tire_type`.
    with pytest.raises(TypeError):
        ctr = CarContainer.create(
            {
                EngineContainer: {"input_host": "abc"},
                WheelContainer: {"tire_type": TireType.SNOW},
            }
        )


def test_perturb_basic() -> None:
    # Perturb container after creation.
    ctr = CarContainer.create(
        {
            EngineContainer: {"input_host": "abc"},
            WheelContainer: {"input_tire_type": TireType.SNOW},
        }
    )

    ctr.engine_ctr.engine = MockEngine()
    ctr["wheel_ctr.snow_tire"] = TireType.SPORT

    car = ctr.car
    assert isinstance(car, DefaultCar)

    # Check that the perturbations override all other values.
    assert isinstance(car.engine, MockEngine)
    assert car.engine is ctr.engine_ctr.engine
    assert (
        not car.wheel0.tire_type == TireType.SPORT
        and not car.wheel1.tire_type == TireType.SPORT
        and not car.wheel2.tire_type == TireType.SPORT
        and not car.wheel3.tire_type == TireType.SPORT
    )

    # Every container is its own instance, i.e.,
    # there are no class-level interactions.
    car1 = CarContainer.create(
        {
            EngineContainer: {"input_host": "abc"},
            WheelContainer: {"input_tire_type": TireType.SNOW},
        }
    ).car
    assert car is not car1
    assert isinstance(car1, DefaultCar)
    assert car1.wheel0.tire_type == TireType.SNOW


@dataclasses.dataclass(frozen=True)
class Foo:
    x: int
    y: float
    z: str


@dataclasses.dataclass(frozen=True)
class Bar:
    foo0: Foo
    foo1: Foo


@container
class ClassicMigrationContainer(Container):
    x: int = 1

    @cache
    def _foo_kwargs0(self) -> dict[str, Any]:
        # Example of delayed collection and partial/lazy kwargs.
        return {"x": self.x}

    @cache
    def _foo_kwargs1(self) -> dict[str, Any]:
        # Example of delayed collection and partial/lazy kwargs.
        return {"y": 10.0}

    @cache
    def foo0(self) -> Foo:
        # Example of combining partial/lazy kwargs.
        return Foo(**self._foo_kwargs0, **self._foo_kwargs1, z="abc")

    @cache
    def bar(self) -> Bar:
        # Second param here is an example of anonymous construction.
        return Bar(foo0=self.foo0, foo1=Foo(5, 20.0, "def"))

    @cache
    def forward_bar(self) -> Bar:
        # Example of forwarding.
        return self.bar

    @cache
    def bar_foo0(self) -> Foo:
        # Example of obj attr.
        return self.bar.foo0


def test_classic_migration() -> None:
    ctr = ClassicMigrationContainer.create()

    # This tests perturbation through partial kwargs and forwards.
    ctr._foo_kwargs0 = {"x": 2}

    assert ctr._foo_kwargs0 == {"x": 2}
    assert ctr.foo0 == Foo(2, 10.0, "abc")

    assert ctr.bar.foo0 is ctr.foo0
    assert ctr.bar.foo1 == Foo(5, 20.0, "def")

    assert ctr.bar is ctr.forward_bar
    assert ctr.bar_foo0 is ctr.foo0


@container
class VeryNestedContainer(Container):
    engine_ctr: EngineContainer

    @cache
    def foo(self) -> Foo:
        return Foo(1, 10.0, z=self.engine_ctr.common_ctr.env)


def test_perturb_very_nested_prototype() -> None:
    ctr = VeryNestedContainer.create({EngineContainer: {"input_host": "abc"}})

    ctr.engine_ctr.common_ctr.env = "prod"

    assert ctr.engine_ctr.common_ctr.env == "prod"
    assert ctr.foo.z == "prod"

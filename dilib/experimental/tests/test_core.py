import abc
import dataclasses
from pathlib import Path

import pytest
from typing_extensions import override

from dilib.experimental import (
    Container,
    FrozenContainerError,
    NewKeyConfigError,
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


@dataclasses.dataclass(frozen=True)
class Wheel:
    snow_tire: bool


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

    @call
    def host(self) -> str:
        return "abc"

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
    input_snow_tire: bool = False

    @call
    def snow_tire(self) -> bool:
        return self.input_snow_tire

    @call
    def wheel(self) -> Wheel:
        return Wheel(self.snow_tire)


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
    ctr = CarContainer.create({WheelContainer: {"input_snow_tire": True}})

    assert ctr.common_ctr is ctr.engine_ctr.common_ctr
    assert ctr.common_ctr is ctr.wheel_ctr.common_ctr

    engine = ctr.engine_ctr.engine
    car = ctr.car
    assert isinstance(car, DefaultCar)

    assert engine is car.engine
    assert (
        car.wheel0.snow_tire
        and car.wheel1.snow_tire
        and car.wheel2.snow_tire
        and car.wheel3.snow_tire
    )
    assert car.wheel0 is not car.wheel1
    assert car.wheel0 is not car.wheel2
    assert car.wheel0 is not car.wheel3
    assert car.wheel0 is not ctr.wheel_ctr.wheel

    with pytest.raises(FrozenContainerError):
        ctr.wheel_ctr.snow_tire = False

    # with pytest.raises(NewKeyConfigError):
    #     ctr.foo = False


def test_perturb() -> None:
    ctr = CarContainer.create({WheelContainer: {"snow_tire": True}})

    ctr.engine_ctr.engine = MockEngine()
    ctr.wheel_ctr.snow_tire = False

    car = ctr.car
    assert isinstance(car, DefaultCar)

    assert isinstance(car.engine, MockEngine)
    assert car.engine is ctr.engine_ctr.engine
    assert (
        not car.wheel0.snow_tire
        and not car.wheel1.snow_tire
        and not car.wheel2.snow_tire
        and not car.wheel3.snow_tire
    )

import abc
import dataclasses
import enum

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


def test_get_set_item() -> None:
    # Use dict-like syntax with dotted keys.
    ctr = CarContainer.create({EngineContainer: {"input_host": "abc"}})

    assert "engine_ctr.engine" in ctr
    engine = ctr["engine_ctr.engine"]
    assert isinstance(engine, DatabaseEngine)

    with pytest.raises(FrozenContainerError):
        ctr["engine_ctr.engine"] = MockEngine()


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

from __future__ import annotations

import abc
import dataclasses
from typing import Any

from typing_extensions import override

import dilib


def get_db_value(_0: Any, _1: Any) -> bool:
    return False


class Seat(dilib.SingletonMixin):
    pass


class Engine(abc.ABC):
    @property
    @abc.abstractmethod
    def started(self) -> bool: ...

    @abc.abstractmethod
    def start(self) -> None: ...


@dataclasses.dataclass(frozen=True)
class DBEngine(Engine, dilib.SingletonMixin):
    db_address: str

    @property
    @override
    def started(self) -> bool:
        return get_db_value(self.db_address, "engine")

    @override
    def start(self) -> None:
        pass


class MockEngine(Engine, dilib.SingletonMixin):
    @property
    @override
    def started(self) -> bool:
        return True

    @override
    def start(self) -> None:
        pass


class Car(dilib.SingletonMixin):
    def __init__(self, seats: list[Seat], engine: Engine) -> None:
        self.seats = seats
        self.engine = engine

        self.state = 0

    def drive(self) -> None:
        if not self.engine.started:
            self.engine.start()
        self.state = 1

    def stop(self) -> None:
        self.state = 0


with dilib.config_context():

    class EngineConfig(dilib.Config):
        db_address = dilib.GlobalInput(type_=str, default="some-db-address")
        engine: Engine = DBEngine(db_address)

    class CarConfig(dilib.Config):
        engine_config = EngineConfig()

        seat0 = Seat()
        seat1 = Seat()
        seats = dilib.SingletonList(seat0, seat1)

        car = Car(seats, engine=engine_config.engine)


def test_basic_demo() -> None:
    config = dilib.get_config(CarConfig, db_address="some-db-address")
    container = dilib.get_container(config)

    car: Car = container.config.car
    assert isinstance(car, Car)
    assert id(car) == id(container.config.car)  # Because it's a Singleton
    assert isinstance(car.engine, DBEngine)


def test_perturb_demo() -> None:
    config = dilib.get_config(CarConfig, db_address="some-db-address")
    config.engine_config.engine = MockEngine()
    container = dilib.get_container(config)

    assert isinstance(container.config.car.engine, MockEngine)

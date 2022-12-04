from __future__ import annotations

import dataclasses
from typing import List

import dilib


def get_db_value(_0, _1) -> bool:
    return False


@dataclasses.dataclass(frozen=True)
class Seat:
    pass


@dataclasses.dataclass(frozen=True)
class Engine:
    @property
    def started(self) -> bool:
        raise NotImplementedError()

    def start(self):
        pass


@dataclasses.dataclass(frozen=True)
class DBEngine(Engine):
    db_address: str

    @property
    def started(self) -> bool:
        return get_db_value(self.db_address, "engine")


@dataclasses.dataclass(frozen=True)
class MockEngine(Engine):
    @property
    def started(self) -> bool:
        return True


@dataclasses.dataclass()
class Car:
    seats: List[Seat]
    engine: Engine
    state: int = 0

    def drive(self):
        if not self.engine.started:
            self.engine.start()
        self.state = 1

    def stop(self):
        self.state = 0


class EngineConfigProtocol(dilib.ConfigProtocol):
    db_address: str = dilib.GlobalInput(type_=str, default="ava-db")
    engine: Engine = dilib.Singleton(DBEngine, db_address=db_address)


class CarConfigProtocol(dilib.ConfigProtocol):
    engine_config: EngineConfigProtocol = dilib.ConfigSpec(
        EngineConfigProtocol
    )

    seat0: Seat = dilib.Singleton(Seat)
    seat1: Seat = dilib.Singleton(Seat)
    seats: List[Seat] = dilib.SingletonList(seat0, seat1)

    car: Car = dilib.Singleton(
        Car,
        seats,
        engine=engine_config.engine,
    )


def test_basic_demo() -> None:
    config: dilib.Config[CarConfigProtocol] = dilib.get_config(
        CarConfigProtocol, db_address="ava-db"
    )
    container: dilib.Container[CarConfigProtocol] = dilib.get_container(config)

    engine: Engine = container.config.engine_config.engine

    car: Car = container.config.car
    assert isinstance(car, Car)
    assert id(car) == id(container.config.car)  # Because it's a Singleton
    assert isinstance(car.engine, DBEngine)
    assert id(car.engine) == id(engine)


def test_perturb_demo():
    config: dilib.Config[CarConfigProtocol] = dilib.get_config(
        CarConfigProtocol, db_address="ava-db"
    )
    assert isinstance(config.engine_config, EngineConfigProtocol)
    config.engine_config.engine = MockEngine()
    container = dilib.get_container(config)

    assert isinstance(container.config.car.engine, MockEngine)

from __future__ import annotations

from typing import List

import dilib


def get_db_value(_0, _1) -> bool:
    return False


class Seat:
    pass


class Engine:
    @property
    def started(self) -> bool:
        raise NotImplementedError()

    def start(self):
        pass


class DBEngine(Engine, dilib.SingletonMixin):
    def __init__(self, db_address: str):
        self.db_address = db_address

    @property
    def started(self) -> bool:
        return get_db_value(self.db_address, "engine")


class MockEngine(Engine, dilib.SingletonMixin):
    @property
    def started(self) -> bool:
        return True


class Car(dilib.SingletonMixin):
    def __init__(self, seats: List[Seat], engine: Engine):
        self.seats = seats
        self.engine = engine

        self.state = 0

    def drive(self):
        if not self.engine.started:
            self.engine.start()
        self.state = 1

    def stop(self):
        self.state = 0


# noinspection PyTypeChecker
class EngineConfig(dilib.Config):

    db_address = dilib.GlobalInput(type_=str, default="ava-db")
    engine = DBEngine(db_address)  # type: ignore


# noinspection PyTypeChecker
class CarConfig(dilib.Config):

    engine_config = EngineConfig()

    seat_cls = dilib.Object(Seat)
    seats = dilib.Prototype(
        lambda cls, n: [cls() for _ in range(n)], seat_cls, 2
    )

    car = Car(seats, engine=engine_config.engine)  # type: ignore


def test_basic_demo():
    config = CarConfig().get(db_address="ava-db")
    container = dilib.Container(config)

    car = container.car
    assert isinstance(car, Car)
    assert id(car) == id(container.car)  # Because it's a Singleton
    assert isinstance(car.engine, DBEngine)


def test_perturb_demo():
    config = CarConfig().get(db_address="ava-db")
    config.engine_config.engine = MockEngine()
    container = dilib.Container(config)

    assert isinstance(container.car.engine, MockEngine)

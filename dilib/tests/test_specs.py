from __future__ import annotations

import abc
from typing import Sequence, TypeVar

from typing_extensions import override

import dilib

T = TypeVar("T")


class BaseMultiplier(abc.ABC):
    @abc.abstractmethod
    def get_result(self) -> int: ...


class SimpleMultiplier(BaseMultiplier):
    def __init__(self, x: int, y: int = 2) -> None:
        self.x = x
        self.y = y

    @override
    def get_result(self) -> int:
        return self.x * self.y


class MockMultipler(BaseMultiplier):
    @override
    def get_result(self) -> int:
        return 42


def add_ints(x: int, y: int) -> int:
    return x + y


def test_typing() -> None:
    spec0: int = dilib.Object(1)
    spec1: int = dilib.Object(2)
    spec2: str = dilib.Object("abc")

    _3: int = dilib.GlobalInput(type_=int)
    _4: str = dilib.LocalInput(type_=str)
    _5: Sequence[str] = dilib.LocalInput(type_=Sequence[str])

    _6: BaseMultiplier = dilib.Prototype(MockMultipler)
    _7: BaseMultiplier = dilib.Prototype(SimpleMultiplier, 100)
    _8: BaseMultiplier = dilib.Singleton(SimpleMultiplier, 100, y=3)
    _9: SimpleMultiplier = dilib.Singleton(SimpleMultiplier, 100, y=3)

    _11: Sequence[int] = dilib.SingletonList(spec0, spec0)
    _12: tuple[str, ...] = dilib.SingletonTuple(spec2, spec2)
    # TODO: Support more narrow `tuple` types?
    # _13: tuple[str, str] = dilib.SingletonTuple(spec2, spec2)
    _14: dict[str, int] = dilib.SingletonDict(a=spec0, b=spec1)

    # Would cause mypy error:
    # _15: str = dilib.Singleton(add_ints, 1, "abc")
    _15: int = dilib.Singleton(add_ints, 1, 2)

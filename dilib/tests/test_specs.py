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

    _3: int = dilib.GlobalInput(type_=int)  # noqa: F841
    _4: str = dilib.LocalInput(type_=str)  # noqa: F841
    _5: Sequence[str] = dilib.LocalInput(type_=Sequence[str])  # noqa: F841

    _6: BaseMultiplier = dilib.Prototype(MockMultipler)  # noqa: F841
    _7: BaseMultiplier = dilib.Prototype(SimpleMultiplier, 100)  # noqa: F841
    _8: BaseMultiplier = dilib.Singleton(  # noqa: F841
        SimpleMultiplier, 100, y=3
    )
    _9: SimpleMultiplier = dilib.Singleton(  # noqa: F841
        SimpleMultiplier, 100, y=3
    )

    _10: Sequence = dilib.SingletonList(spec0, spec0)  # noqa: F841
    _11: Sequence[int] = dilib.SingletonList(spec0, spec0)  # noqa: F841
    _12: tuple = dilib.SingletonTuple(spec2, spec2)  # noqa: F841
    # TODO: Support more narrow Tuple types
    # _13: Tuple[str, str] = dilib.SingletonTuple(spec2, spec2)  # noqa: F841
    _14: dict = dilib.SingletonDict(a=spec0, b=spec1)  # noqa: F841
    _15: dict[str, int] = dilib.SingletonDict(a=spec0, b=spec1)  # noqa: F841

    # Would cause mypy error:
    # _16: str = dilib.Singleton(add_ints, 1, "abc")  # noqa: F841
    _16: int = dilib.Singleton(add_ints, 1, 2)  # noqa: F841

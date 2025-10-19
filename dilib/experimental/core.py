from __future__ import annotations

import abc
import dataclasses
import functools
import itertools
from typing import (
    Callable,
    ClassVar,
    Generic,
    Iterable,
    TypeVar,
    cast,
    get_type_hints,
    overload,
)
import weakref

from typing_extensions import Self, override

T = TypeVar("T")
R = TypeVar("R")

PRIVATE_CONTAINER_FIELD_NAMES = {
    "_frozen",
    "_instance_cache",
    "_parent_ctrs",
    "_field_keys",
    "_child_ctr_keys",
    "_property_keys",
}


class ContainerError(RuntimeError):
    pass


class FrozenContainerError(ContainerError):
    pass


def nested_func(
    ctr: Container, key: str, func: Callable[[Container, str], R]
) -> R:
    key_split = key.split(".")
    for idx, key_part in enumerate(key_split):
        if idx < len(key_split) - 1:
            obj = getattr(ctr, key_part)
            if not isinstance(obj, Container):
                raise TypeError(type(obj))

            ctr = obj
        else:
            return func(ctr, key_part)

    raise RuntimeError("Reached unexpected point")


@dataclasses.dataclass(kw_only=True)
class Container:
    _frozen: bool = dataclasses.field(
        default=False, init=False, hash=False, compare=False, repr=False
    )
    _instance_cache: dict[str, object] = dataclasses.field(
        default_factory=dict, init=False, hash=False, compare=False, repr=False
    )
    _parent_ctrs: weakref.WeakSet[Container] = dataclasses.field(
        default_factory=weakref.WeakSet,
        init=False,
        hash=False,
        compare=False,
        repr=False,
    )

    _field_keys: ClassVar[set[str]]
    _child_ctr_keys: ClassVar[set[str]]
    _property_keys: ClassVar[set[str]]

    @property
    def _child_ctrs(self) -> Iterable[Container]:
        for key in self._child_ctr_keys:
            yield getattr(self, key)

    @functools.cached_property
    def keys(self) -> set[str]:
        return self._field_keys.union(self._property_keys)

    def freeze(self) -> None:
        if self._frozen:
            return

        self._frozen = True

        for ctr in itertools.chain(self._parent_ctrs, self._child_ctrs):
            ctr.freeze()

    def _check_not_frozen(self) -> None:
        if self._frozen:
            raise FrozenContainerError(
                "Container is already frozen, "
                + "either because a value was already gotten or "
                + "`freeze()` was directly called"
            )

    def _get(self, key: str) -> object:
        if key not in self.keys:
            raise KeyError(key)

        self._check_not_frozen()

        return getattr(self, key)

    def get(
        self, key: str, *, default: object = dataclasses.MISSING
    ) -> object:
        try:
            return self._get(key)
        except KeyError:
            if default is dataclasses.MISSING:
                raise
            else:
                return default

    def _set(self, key: str, value: object) -> None:
        self._check_not_frozen()

        setattr(self, key, value)

    def __getitem__(self, key: str) -> object:
        return nested_func(self, key, lambda ctr, key_part: ctr._get(key_part))

    def __contains__(self, key: str) -> bool:
        return nested_func(
            self, key, lambda ctr, key_part: key_part in ctr.keys
        )

    def __setitem__(self, key: str, value: object) -> None:
        nested_func(self, key, lambda ctr, key_part: ctr._set(key_part, value))

    @override
    def __hash__(self) -> int:
        return hash(self.__class__)

    @classmethod
    def _create(
        cls: type[TC],
        ctr_cache: dict[type[Container], Container],
        params: dict[type[Container], dict[str, object]] | None = None,
    ) -> TC:
        try:
            return cast(TC, ctr_cache[cls])
        except KeyError:
            pass

        cls_params = params.get(cls) if params is not None else None
        cls_annotations = get_type_hints(cls)

        field_keys: set[str] = set()
        child_ctrs: dict[str, Container] = {}

        ctr_kwargs: dict[str, object] = {}
        for field in dataclasses.fields(cls):
            if field.name not in PRIVATE_CONTAINER_FIELD_NAMES:
                field_keys.add(field.name)

            field_annotation = cls_annotations[field.name]

            if isinstance(field_annotation, type) and issubclass(
                field_annotation, Container
            ):
                if (
                    field.default is not dataclasses.MISSING
                    or field.default_factory is not dataclasses.MISSING
                ):
                    raise ValueError(
                        "Cannot set defaults for child containers"
                    )

                child_ctr = field_annotation._create(ctr_cache, params=params)
                child_ctrs[field.name] = child_ctr
                ctr_kwargs[field.name] = child_ctr
            elif cls_params is not None and field.name in cls_params:
                ctr_kwargs[field.name] = cls_params[field.name]

        cls._field_keys = field_keys
        cls._child_ctr_keys = set(child_ctrs)
        ctr = cls(**ctr_kwargs)

        for child_ctr in child_ctrs.values():
            child_ctr._parent_ctrs.add(ctr)

        ctr_cache[cls] = ctr
        return ctr

    @classmethod
    def create(
        cls: type[TC],
        params: dict[type[Container], dict[str, object]] | None = None,
    ) -> TC:
        return cls._create(ctr_cache={}, params=params)


TC = TypeVar("TC", bound=Container)


@dataclasses.dataclass(frozen=True)
class PropertyValue(abc.ABC, Generic[TC, R]):
    func: Callable[[TC], R]

    @property
    def key(self) -> str:
        return self.func.__name__

    @abc.abstractmethod
    def _get(self, obj: TC) -> R: ...

    def __set_name__(self, owner: type[TC], name: str) -> None:
        if not hasattr(owner, "_property_keys"):
            owner._property_keys = set()
        owner._property_keys.add(self.key)

    @overload
    def __get__(self, obj: None, obj_type: type[TC]) -> Self: ...

    @overload
    def __get__(self, obj: TC, obj_type: type[TC] | None = None) -> R: ...

    def __get__(
        self, obj: TC | None, obj_type: type[TC] | None = None
    ) -> R | Self:
        if obj is None:
            return self

        return self._get(obj)

    def __set__(self, obj: TC, value: R) -> None:
        obj._check_not_frozen()

        obj._instance_cache[self.key] = value


@dataclasses.dataclass(frozen=True)
class Prototype(PropertyValue[TC, R]):
    @override
    def _get(self, obj: TC) -> R:
        obj.freeze()

        return self.func(obj)


@dataclasses.dataclass(frozen=True)
class Singleton(PropertyValue[TC, R]):
    @override
    def _get(self, obj: TC) -> R:
        obj.freeze()

        try:
            value = cast(R, obj._instance_cache[self.key])
        except KeyError:
            value = self.func(obj)
            obj._instance_cache[self.key] = value

        return value


def call(func: Callable[[TC], R]) -> Prototype[TC, R]:
    return Prototype(func)


def cache(func: Callable[[TC], R]) -> Singleton[TC, R]:
    return Singleton(func)


def container(cls: type[T]) -> type[T]:
    return dataclasses.dataclass(frozen=False, unsafe_hash=True)(cls)

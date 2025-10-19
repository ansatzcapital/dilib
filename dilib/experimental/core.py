from __future__ import annotations

import dataclasses
import itertools
import json
from pathlib import Path
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

import cattrs
from typing_extensions import Self, override

T = TypeVar("T")
R = TypeVar("R")


class ContainerError(RuntimeError):
    pass


class NewKeyConfigError(ContainerError):
    pass


class FrozenContainerError(ContainerError):
    pass


def nested_func(
    ctr: Container, key: str, func: Callable[[Container, str], R]
) -> R:
    key_split = key.split(".")
    for idx, key_part in enumerate(key_split):
        if idx < len(key_split) - 1:
            obj = ctr._get_value(key_part)
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

    _field_names: ClassVar[set[str]]
    _keys: ClassVar[set[str]]

    @property
    def _child_ctrs(self) -> Iterable[Container]:
        for field in dataclasses.fields(self):
            field_value = getattr(self, field.name)
            if isinstance(field_value, Container):
                yield field_value

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

    def _get_value(self, key: str, *, via_get_attr: bool = False) -> object:
        if key in self._field_names:
            return getattr(self, key)

        if via_get_attr:
            return getattr(self, key)
        else:
            return self._instance_cache[key]

    def _get_value_impl(
        self, key: str, *, via_get_attr: bool = False
    ) -> object:
        self.freeze()

        return nested_func(
            self,
            key,
            lambda obj, key_part: obj._get_value(
                key_part, via_get_attr=via_get_attr
            ),
        )

    def get_value(self, key: str) -> object:
        return self._get_value_impl(key)

    def _contains_key(self, key: str) -> bool:
        return key in self._field_names or key in self._keys

    def contains_key(self, key: str) -> bool:
        return nested_func(
            self, key, lambda obj, key_part: obj._contains_key(key_part)
        )

    def _set_value(self, key: str, value: object) -> None:
        if key not in self._keys:
            raise NewKeyConfigError(key)

        self._instance_cache[key] = value

    def set_value(self, key: str, value: object) -> None:
        self._check_not_frozen()

        nested_func(
            self,
            key,
            lambda obj, key_part: obj._set_value(key_part, value),
        )

    def __contains__(self, key: str) -> bool:
        return self.contains_key(key)

    def __getitem__(self, key: str) -> object:
        return self._get_value_impl(key, via_get_attr=True)

    def __setitem__(self, key: str, value: object) -> None:
        self.set_value(key, value)

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

        field_names: set[str] = set()
        ctr_kwargs: dict[str, object] = {}
        child_ctrs: list[Container] = []
        for field in dataclasses.fields(cls):
            field_names.add(field.name)

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
                child_ctrs.append(child_ctr)
                ctr_kwargs[field.name] = child_ctr
            elif cls_params is not None and field.name in cls_params:
                ctr_kwargs[field.name] = cls_params[field.name]

        cls._field_names = field_names
        ctr = cls(**ctr_kwargs)
        # ctr._loaded = True

        for child_ctr in child_ctrs:
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
class Prototype(Generic[TC, R]):
    func: Callable[[TC], R]

    @property
    def key(self) -> str:
        return self.func.__name__

    def __set_name__(self, owner: type[TC], name: str) -> None:
        if not hasattr(owner, "_keys"):
            owner._keys = set()
        owner._keys.add(self.key)

    @overload
    def __get__(self, obj: None, obj_type: type[TC]) -> Self: ...

    @overload
    def __get__(self, obj: TC, obj_type: type[TC] | None = None) -> R: ...

    def __get__(
        self, obj: TC | None, obj_type: type[TC] | None = None
    ) -> R | Self:
        if obj is None:
            return self

        return self.func(obj)

    def __set__(self, obj: TC, value: R) -> None:
        obj.set_value(self.key, value)


@dataclasses.dataclass(frozen=True)
class Singleton(Generic[TC, R]):
    func: Callable[[TC], R]

    @property
    def key(self) -> str:
        return self.func.__name__

    def __set_name__(self, owner: type[TC], name: str) -> None:
        if not hasattr(owner, "_keys"):
            owner._keys = set()
        owner._keys.add(self.key)

    @overload
    def __get__(self, obj: None, obj_type: type[TC]) -> Self: ...

    @overload
    def __get__(self, obj: TC, obj_type: type[TC] | None = None) -> R: ...

    def __get__(
        self, obj: TC | None, obj_type: type[TC] | None = None
    ) -> R | Self:
        if obj is None:
            return self

        try:
            value = cast(R, obj.get_value(self.key))
        except KeyError:
            value = self.func(obj)
            obj._instance_cache[self.key] = value

        return value

    def __set__(self, obj: TC, value: R) -> None:
        obj.set_value(self.key, value)


def call(func: Callable[[TC], R]) -> Prototype[TC, R]:
    return Prototype(func)


def cache(func: Callable[[TC], R]) -> Singleton[TC, R]:
    return Singleton(func)


def container(cls: type[T]) -> type[T]:
    return dataclasses.dataclass(unsafe_hash=True)(cls)


# def load_config(value: T | str | Path, cls: type[T]) -> T:
#     if isinstance(value, (str, Path)):
#         converter = cattrs.Converter()
#         data = json.load(Path(value).open("rb"))
#         return converter.structure(data, cls)

#     return value

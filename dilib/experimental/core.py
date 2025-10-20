# ruff: noqa: UP006
from __future__ import annotations

import abc
import dataclasses
import functools
import itertools
from typing import (
    TYPE_CHECKING,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    Set,
    Type,
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


class ContainerParamsError(ContainerError):
    """Either missing or extra container param."""

    pass


class FrozenContainerError(ContainerError):
    """Once frozen, a container cannot be perturbed.

    Freezing happens when either (1) the user call `Container.freeze()`,
    or (2) whenever any value in the container hierarchy is gotten.
    The latter is to ensure a self-consistency guarantee
    (i.e., every perturb is guaranteed to be reflected in every
    downstream object).
    """

    pass


class NewContainerKeyError(ContainerError):
    """Cannot add a new key not specified by container author."""

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


@dataclasses.dataclass()
class Container:
    """Create and cache (if necessary) objects.

    The author of the child `Container` class describes a universe
    of objects that depend on each other, and the container user can retrieve
    any object in this universe by name.
    """

    _frozen: bool = dataclasses.field(
        default=False, init=False, hash=False, compare=False, repr=False
    )
    _instance_cache: Dict[str, object] = dataclasses.field(
        default_factory=dict, init=False, hash=False, compare=False, repr=False
    )
    _parent_ctrs: ContainerWeakSet = dataclasses.field(
        default_factory=weakref.WeakSet,
        init=False,
        hash=False,
        compare=False,
        repr=False,
    )

    _field_keys: ClassVar[Set[str]]
    _child_ctr_keys: ClassVar[Set[str]]
    _property_keys: ClassVar[Set[str]]

    @property
    def _child_ctrs(self) -> Iterable[Container]:
        for key in self._child_ctr_keys:
            yield getattr(self, key)

    @functools.cached_property
    def _keys(self) -> Set[str]:
        if hasattr(self.__class__, "_property_keys"):
            return self._field_keys.union(self._property_keys)
        else:
            return self._field_keys

    def keys(self) -> Iterable[str]:
        """Available fields and properties (shallow).

        By shallow, we mean we don't recurse down to child containers,
        which are also available keys to the user.
        """
        return self._keys

    def freeze(self) -> None:
        """Prevent any further perturbations."""
        if self._frozen:
            return

        self._frozen = True

        for ctr in itertools.chain(self._parent_ctrs, self._child_ctrs):
            ctr.freeze()

    def _check_not_frozen(self) -> None:
        if self._frozen:
            raise FrozenContainerError(
                "Container is already frozen, "
                + "either because a value was already retrieved or "
                + "`freeze()` was directly called"
            )

    def _get(self, key: str) -> object:
        if key not in self.keys():
            raise KeyError(key)

        self._check_not_frozen()

        return getattr(self, key)

    def get(
        self, key: str, *, default: object = dataclasses.MISSING
    ) -> object:
        """Create and cache (if necessary) object with given key."""
        try:
            return self._get(key)
        except KeyError:
            if default is dataclasses.MISSING:
                raise
            else:
                return default

    def _check_before_set(self, key: str) -> None:
        self._check_not_frozen()

        if key not in self.keys():
            raise NewContainerKeyError(
                f"Cannot set new key on container: {key!r}"
            )

    def _set(self, key: str, value: object) -> None:
        self._check_before_set(key)

        setattr(self, key, value)

    def __getitem__(self, key: str) -> object:
        return nested_func(self, key, lambda ctr, key_part: ctr._get(key_part))

    def __contains__(self, key: str) -> bool:
        return nested_func(
            self, key, lambda ctr, key_part: key_part in ctr.keys()
        )

    def __setitem__(self, key: str, value: object) -> None:
        nested_func(self, key, lambda ctr, key_part: ctr._set(key_part, value))

    @override
    def __setattr__(self, key: str, value: object) -> None:
        if key in PRIVATE_CONTAINER_FIELD_NAMES:
            return super().__setattr__(key, value)

        self._check_before_set(key)

        return super().__setattr__(key, value)

    @override
    def __hash__(self) -> int:
        return hash(self.__class__)

    @classmethod
    def _create(
        cls: Type[TC],
        ctr_cache: Dict[Type[Container], Container],
        params: Dict[Type[Container], Dict[str, object]] | None = None,
    ) -> TC:
        try:
            return cast(TC, ctr_cache[cls])
        except KeyError:
            pass

        cls_params = params.get(cls) if params is not None else None
        cls_annotations = get_type_hints(cls)

        field_keys: Set[str] = set()
        child_ctrs: Dict[str, Container] = {}

        ctr_kwargs: Dict[str, object] = {}
        for field in dataclasses.fields(cls):
            if field.name in PRIVATE_CONTAINER_FIELD_NAMES:
                continue
            else:
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

        # NB: If there are either extra or missing params for this class,
        # Python will raise a `TypeError` when we construct it below.
        if cls_params is not None:
            ctr_kwargs.update(cls_params)

        cls._field_keys = field_keys
        cls._child_ctr_keys = set(child_ctrs)
        ctr = cls(**ctr_kwargs)

        for child_ctr in child_ctrs.values():
            child_ctr._parent_ctrs.add(ctr)

        ctr_cache[cls] = ctr
        return ctr

    @classmethod
    def create(
        cls: Type[TC],
        params: Dict[Type[Container], Dict[str, object]] | None = None,
    ) -> TC:
        """Create container and its child containers (cached by type).

        E.g.:

        ```python
        ctr = ParentContainer.create({ChildContainer: {"foo": 123}})
        ```
        """
        return cls._create(ctr_cache={}, params=params)


TC = TypeVar("TC", bound=Container)

if TYPE_CHECKING:
    ContainerWeakSet = weakref.WeakSet[Container]
else:
    ContainerWeakSet = weakref.WeakSet


@dataclasses.dataclass(frozen=True)
class PropertyValue(abc.ABC, Generic[TC, R]):
    func: Callable[[TC], R]

    @property
    def key(self) -> str:
        return self.func.__name__

    @abc.abstractmethod
    def _get(self, obj: TC) -> R: ...

    def __set_name__(self, owner: Type[TC], name: str) -> None:
        if not hasattr(owner, "_property_keys"):
            owner._property_keys = set()
        owner._property_keys.add(self.key)

    @overload
    def __get__(self, obj: None, obj_type: Type[TC]) -> Self: ...

    @overload
    def __get__(self, obj: TC, obj_type: Type[TC] | None = None) -> R: ...

    def __get__(
        self, obj: TC | None, obj_type: Type[TC] | None = None
    ) -> R | Self:
        if obj is None:
            return self

        return self._get(obj)

    def __set__(self, obj: TC, value: R) -> None:
        obj._check_before_set(self.key)

        obj._instance_cache[self.key] = value


@dataclasses.dataclass(frozen=True)
class Prototype(PropertyValue[TC, R]):
    @override
    def _get(self, obj: TC) -> R:
        obj.freeze()

        # Even though we never cache the result of this func call,
        # we use the instance cache to communicate that it's been
        # perturbed by the user.
        try:
            return cast(R, obj._instance_cache[self.key])
        except KeyError:
            pass

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
    """Call this method every time this object is retrieved."""
    return Prototype(func)


def cache(func: Callable[[TC], R]) -> Singleton[TC, R]:
    """Call this method once upon first retrieval and cache for later use."""
    return Singleton(func)


def container(cls: Type[T]) -> Type[T]:
    """Decorate container to enable field values."""
    return dataclasses.dataclass(frozen=False, unsafe_hash=True)(cls)

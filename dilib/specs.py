from __future__ import annotations

from typing import Any, Callable, Generic, List, Optional, Type, TypeVar, cast

MISSING = object()

SpecID = int
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


def instantiate(cls: type, *args, **kwargs) -> Any:
    """Instantiate obj from Spec parts."""
    if cls in (list, tuple):
        return cls(args)
    elif cls is dict:
        return cls(kwargs)
    else:
        # noinspection PyTypeChecker
        obj = object.__new__(cls)

    try:
        obj.__init__(*args, **kwargs)
    except TypeError as exc:
        raise TypeError(f"{cls}: {str(exc)}")

    return obj


class AttrFuture:
    """Future representing attr access on a Spec."""

    def __init__(self, parent_spec_id: SpecID, attrs: List[str]):
        self.parent_spec_id = parent_spec_id
        self.attrs = attrs

    def __getattr__(self, attr: str) -> AttrFuture:
        return AttrFuture(self.parent_spec_id, self.attrs + [attr])


class Spec(Generic[T]):
    """Represents delayed obj to be instantiated later."""

    NEXT_SPEC_ID = 0

    def __init__(self):
        self.spec_id = self._get_next_spec_id()

    def __getattr__(self, attr: str) -> AttrFuture:
        return AttrFuture(self.spec_id, [attr])

    @staticmethod
    def _get_next_spec_id() -> SpecID:
        result = Spec.NEXT_SPEC_ID
        Spec.NEXT_SPEC_ID += 1
        return result


class _Object(Spec[T]):
    """Represents fully-instantiated obj."""

    def __init__(self, obj: T):
        super().__init__()
        self.obj = obj


# noinspection PyPep8Naming
def Object(obj: T) -> T:
    # Cast because the return type will act like a U
    return cast(T, _Object(obj))


class _Input(Spec[T]):
    """Represents global input that can be set while getting Config."""

    def __init__(
        self, type_: Optional[Type[T]] = None, default: Any = MISSING
    ):
        super().__init__()
        self.type_ = type_
        self.default = default


class _GlobalInput(_Input[T]):
    pass


# noinspection PyPep8Naming
def GlobalInput(type_: Optional[Type[T]] = None, default: Any = MISSING) -> T:
    # Cast because the return type will act like a T
    return cast(T, _GlobalInput(type_=type_, default=default))


class _LocalInput(_Input[T]):
    pass


# noinspection PyPep8Naming
def LocalInput(type_: Optional[Type[T]] = None, default: Any = MISSING) -> T:
    # Cast because the return type will act like a T
    return cast(T, _LocalInput(type_=type_, default=default))


class _Prototype(Spec[T]):
    """Represents obj to be instantiated at every Container get call."""

    def __init__(self, cls: Callable[..., T], *args, **kwargs):
        super().__init__()
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    def instantiate(self) -> Any:
        """Instantiate, useful when using outside DI framework."""
        if isinstance(self.cls, type):
            return instantiate(self.cls, *self.args, **self.kwargs)
        else:
            # Non-type callable (e.g., function, functor)
            return self.cls(*self.args, **self.kwargs)  # noqa

    def copy_with(self, *args, **kwargs) -> _Prototype:
        return self.__class__(self.cls, *args, **kwargs)


# noinspection PyPep8Naming
def Prototype(cls: Callable[..., T], *args, **kwargs) -> T:
    # Cast because the return type will act like a T
    return cast(T, _Prototype(cls, *args, **kwargs))


def identity(obj: T) -> T:
    return obj


# noinspection PyPep8Naming
def Forward(obj: T) -> T:
    # Cast because the return type will act like a T
    return cast(T, _Prototype(identity, obj))


class _Singleton(_Prototype[T]):
    """Represents obj to be instantiated once per key per Container."""

    pass


# noinspection PyPep8Naming
def Singleton(cls: Callable[..., T], *args, **kwargs) -> T:
    # Cast because the return type will act like a T
    return cast(T, _Singleton(cls, *args, **kwargs))


# noinspection PyPep8Naming
def SingletonTuple(*args) -> T:
    # Cast because the return type will act like a T
    # noinspection PyTypeChecker
    return cast(T, _Singleton(tuple, *args))


# noinspection PyPep8Naming
def SingletonList(*args) -> T:
    # Cast because the return type will act like a T
    # noinspection PyTypeChecker
    return cast(T, _Singleton(list, *args))


# noinspection PyPep8Naming
def SingletonDict(**kwargs) -> T:
    # Cast because the return type will act like a T
    # noinspection PyTypeChecker
    return cast(T, _Singleton(dict, **kwargs))


class PrototypeMixin:
    """Helper class for Prototype to ease syntax in Config."""

    def __new__(cls: type, *args, **kwargs):
        return Prototype(cls, *args, **kwargs)


class SingletonMixin:
    """Helper class for Singleton to ease syntax in Config."""

    def __new__(cls: type, *args, **kwargs):
        return Singleton(cls, *args, **kwargs)

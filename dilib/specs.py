from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from typing_extensions import ParamSpec

MISSING = object()
MISSING_DICT: Dict = dict()  # Need a special typed sentinel for mypy

SpecID = int
P = ParamSpec("P")
T = TypeVar("T")


def instantiate(cls: Type[T], *args, **kwargs) -> T:
    """Instantiate obj from Spec parts."""
    try:
        if issubclass(
            cls,
            (PrototypeMixin, SingletonMixin),
        ):
            obj = cls.__new__(cls, _materialize=True)
            obj.__init__(*args, **kwargs)
            return obj

        return cls(*args, **kwargs)
    except TypeError as exc:
        raise TypeError(f"{cls}: {str(exc)}") from None


class AttrFuture:
    """Future representing attr access on a Spec by its spec id."""

    def __init__(self, root_spec_id: SpecID, attrs: List[str]):
        self.root_spec_id = root_spec_id
        self.attrs = attrs

    def __getattr__(self, attr: str) -> AttrFuture:
        return AttrFuture(self.root_spec_id, self.attrs + [attr])


class Spec(Generic[T]):
    """Represents delayed object to be instantiated later."""

    NEXT_SPEC_ID = 0

    def __init__(self, spec_id: Optional[SpecID] = None):
        self.spec_id = self._get_next_spec_id() if spec_id is None else spec_id

    def __getattr__(self, attr: str) -> AttrFuture:
        return AttrFuture(self.spec_id, [attr])

    # For mypy
    def __call__(self, *args, **kwargs) -> Any:
        return None

    @classmethod
    def _get_next_spec_id(cls) -> SpecID:
        # NB: Need to use Spec explicitly to ensure all Spec
        # subclasses share the same spec id space.
        result = Spec.NEXT_SPEC_ID
        Spec.NEXT_SPEC_ID += 1
        return result


class _Object(Spec[T]):
    """Represents fully-instantiated object to pass through."""

    def __init__(self, obj: T, spec_id: Optional[SpecID] = None):
        super().__init__(spec_id=spec_id)
        self.obj = obj


# noinspection PyPep8Naming
def Object(obj: T) -> T:
    """Spec to pass through a fully-instantiated object.

    Args:
        obj: Fully-instantiated object to pass through.
    """
    # Cast because the return type will act like a T
    return cast(T, _Object(obj))


class _Input(Spec[T]):
    """Represents user input to config."""

    def __init__(
        self, type_: Optional[Type[T]] = None, default: Any = MISSING
    ):
        super().__init__()
        self.type_ = type_
        self.default = default


class _GlobalInput(_Input[T]):
    """Represents input passed in at config instantiation."""

    pass


# noinspection PyPep8Naming
def GlobalInput(type_: Optional[Type[T]] = None, default: Any = MISSING) -> T:
    """Spec to use user input passed in at config instantiation.

    Args:
        type_: Expected type of input, for both static and runtime check.
        default: Default value if no input is provided.
    """
    # Cast because the return type will act like a T
    return cast(T, _GlobalInput(type_=type_, default=default))


class _LocalInput(_Input[T]):
    """Represents input passed in at config declaration."""

    pass


# noinspection PyPep8Naming
def LocalInput(type_: Optional[Type[T]] = None, default: Any = MISSING) -> T:
    """Spec to use user input passed in at config declaration.

    Args:
        type_: Expected type of input, for both static and runtime check.
        default: Default value if no input is provided.
    """
    # Cast because the return type will act like a T
    return cast(T, _LocalInput(type_=type_, default=default))


class _Callable(Spec[T]):
    """Represents callable (e.g., func, type) to be called with given args."""

    def __init__(
        self,
        func_or_type: Callable[..., T],
        *args,
        **kwargs,
    ):
        super().__init__()
        self.func_or_type = func_or_type
        self.args = args
        self.lazy_kwargs = kwargs.pop("__lazy_kwargs", None)
        self.kwargs = kwargs

    def instantiate(self) -> Any:
        """Instantiate spec into object."""
        if isinstance(self.func_or_type, type):
            # noinspection PyTypeChecker
            return instantiate(self.func_or_type, *self.args, **self.kwargs)
        else:
            # Non-type callable (e.g., function, functor)
            return self.func_or_type(*self.args, **self.kwargs)

    def copy_with(self, *args, **kwargs) -> _Callable:
        """Make a copy with replaced args.

        Used to replace arg specs with materialized args.
        """
        return self.__class__(self.func_or_type, *args, **kwargs)


class _Prototype(_Callable[T]):
    pass


# noinspection PyPep8Naming
def Prototype(
    func_or_type: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    """Spec to call with args and no caching."""
    # Cast because the return type will act like a T
    return cast(T, _Prototype(func_or_type, *args, **kwargs))


def _identity(obj: T) -> T:
    return obj


def _union_dict_and_kwargs(values: Dict, **kwargs) -> Dict:
    new_values = values.copy()
    new_values.update(**kwargs)
    return new_values


# noinspection PyPep8Naming
def Forward(obj: T) -> T:
    """Spec to simply forward to other spec."""
    # Cast because the return type will act like a T
    return cast(T, _Prototype(_identity, obj))


class _Singleton(_Callable[T]):
    pass


# noinspection PyPep8Naming
def Singleton(
    func_or_type: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    """Spec to call with args and caching per config field."""
    # Cast because the return type will act like a T
    return cast(T, _Singleton(func_or_type, *args, **kwargs))


# noinspection PyPep8Naming
def SingletonTuple(*args) -> Tuple:
    """Spec to create tuple with args and caching per config field."""
    # Cast because the return type will act like a TT
    return cast(Tuple, _Singleton(tuple, args))


# noinspection PyPep8Naming
def SingletonList(*args) -> List:
    """Spec to create list with args and caching per config field."""
    # Cast because the return type will act like a TL
    return cast(List, _Singleton(list, args))


# TODO: If we drop python3.7, we can use the positional-only params
#   functionality introduced in python3.8 to distringuish between
#   dilib.SingletonDict(values=1), which represents {"values": 1},
#   and positional values like dilib.SingletonDict({"a": 1}).
# noinspection PyPep8Naming
def SingletonDict(
    values: Dict = MISSING_DICT,  # noqa
    **kwargs,
) -> Dict:
    """Spec to create dict with args and caching per config field.

    Can specify either by pointing to a dict, passing in kwargs,
    or unioning both.

    >>> import dilib
    >>> spec0 = dilib.Object(1); spec1 = dilib.Object(2)
    >>> dilib.SingletonDict({"x": spec0, "y": spec1}) is not None
    True

    Or, alternatively:

    >>> dilib.SingletonDict(x=spec0, y=spec1) is not None
    True
    """
    if values is MISSING:
        # Cast because the return type will act like a TD
        return cast(Dict, _Singleton(dict, **kwargs))
    else:
        # Cast because the return type will act like a TD
        return cast(
            Dict,
            _Singleton(_union_dict_and_kwargs, values, **kwargs),
        )


class PrototypeMixin:
    """Helper class for Prototype to ease syntax in Config.

    Equivalent to dilib.Prototype(cls, ...).
    """

    def __new__(cls: Type, *args, _materialize: bool = False, **kwargs):
        if _materialize:
            # noinspection PyTypeChecker
            return super().__new__(cls)
        else:
            return Prototype(cls, *args, **kwargs)


class SingletonMixin:
    """Helper class for Singleton to ease syntax in Config.

    Equivalent to dilib.Singleton(cls, ...).
    """

    def __new__(cls: Type, *args, _materialize: bool = False, **kwargs):
        if _materialize:
            # noinspection PyTypeChecker
            return super().__new__(cls)
        else:
            return Singleton(cls, *args, **kwargs)

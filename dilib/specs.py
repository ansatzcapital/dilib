"""Specs are recipes of how objects should be created.

The public functions are named like classes (e.g., :func:`Object`,
:func:`Singleton`), while the actual specs are private classes
with underscore prefixes. This mimics the pattern seen in
`dataclasses.field()` func vs. `dataclass.Field` class.

Note that we "trick" IDEs and static type checkers by casting
the spec objects into whatever type they will return when instantiated
by the container. Although a bit inelegant, this actually makes
all the config wiring type check exactly as expected.
"""

from __future__ import annotations

import contextlib
from typing import Any, Callable, Generator, Generic, TypeVar, cast

from typing_extensions import ParamSpec, Self, TypeAlias, override

import dilib.errors

MATERIALIZE = True

MISSING = object()

SpecID: TypeAlias = int
P = ParamSpec("P")
T = TypeVar("T")


def instantiate(cls: type[T], *args: Any, **kwargs: Any) -> T:
    """Instantiate obj from Spec parts.

    :meta private:
    """
    try:
        if issubclass(
            cls,
            (PrototypeMixin, SingletonMixin),
        ):
            obj = cls.__new__(cls, _materialize=True)
            obj.__init__(*args, **kwargs)  # noqa
            return cast(T, obj)

        return cls(*args, **kwargs)
    except TypeError as exc:
        raise TypeError(f"{cls}: {str(exc)}") from None


class AttrFuture:
    """Future representing attr access on a Spec by its spec id.

    :meta private:
    """

    def __init__(self, root_spec_id: SpecID, attrs: list[str]) -> None:
        self.root_spec_id = root_spec_id
        self.attrs = attrs

    def __getattr__(self, attr: str) -> AttrFuture:
        return AttrFuture(self.root_spec_id, self.attrs + [attr])


class Spec(Generic[T]):
    """Represents delayed object to be instantiated later.

    Use one of child classes when describing objects.
    """

    _INTERNAL_FIELDS = ["spec_id"]
    NEXT_SPEC_ID = 0

    def __init__(self, spec_id: SpecID | None = None) -> None:
        self.spec_id = self._get_next_spec_id() if spec_id is None else spec_id

    def __getattr__(self, attr: str) -> AttrFuture:
        return AttrFuture(self.spec_id, [attr])

    @override
    def __setattr__(self, name: str, value: Any) -> None:
        if (
            name.startswith("__")
            or name == "_INTERNAL_FIELDS"
            or name in self._INTERNAL_FIELDS
        ):
            return super().__setattr__(name, value)

        # NB: We considered supporting this kind of perturbation,
        # but the issue is that we don't know whether the config
        # this spec is attached to has been frozen. For sake of safety
        # and simplicity, we raise an error here instead.
        raise dilib.errors.PerturbSpecError(
            "Cannot set on a spec. "
            "If you'd like to perturb a value used by a spec, "
            "promote it to be a config field and perturb the config instead."
        )

    # For mypy
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return None

    @classmethod
    def _get_next_spec_id(cls) -> SpecID:
        # NB: Need to use `Spec` explicitly to ensure all `Spec`
        # subclasses share the same spec id space.
        result = Spec.NEXT_SPEC_ID
        Spec.NEXT_SPEC_ID += 1
        return result


class _Object(Spec[T]):
    """Represents fully-instantiated object to pass through."""

    _INTERNAL_FIELDS = Spec._INTERNAL_FIELDS + ["obj"]

    def __init__(self, obj: T, spec_id: SpecID | None = None) -> None:
        super().__init__(spec_id=spec_id)
        self.obj = obj


# noinspection PyPep8Naming
def Object(obj: T) -> T:  # noqa: N802
    """Spec to pass through a fully-instantiated object.

    >>> class FooConfig(dilib.Config):
    ...     x = dilib.Object(1)

    Args:
        obj: Fully-instantiated object to pass through.
    """
    # Cast because the return type will act like a T
    return cast(T, _Object(obj))


class _Input(Spec[T]):
    """Represents user input to config."""

    _INTERNAL_FIELDS = Spec._INTERNAL_FIELDS + ["type_", "default"]

    def __init__(
        self, type_: type[T] | None = None, default: Any = MISSING
    ) -> None:
        super().__init__()
        self.type_ = type_
        self.default = default


class _GlobalInput(_Input[T]):
    """Represents input passed in at config instantiation."""

    pass


# noinspection PyPep8Naming
def GlobalInput(  # noqa: N802
    type_: type[T] | None = None, default: Any = MISSING
) -> T:
    """Spec to use user input passed in at config instantiation.

    >>> class FooConfig(dilib.Config):
    ...     x = dilib.GlobalInput(type_=str)
    ...     y = dilib.GlobalInput(type_=int, default=1)

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
def LocalInput(  # noqa: N802
    type_: type[T] | None = None, default: Any = MISSING
) -> T:
    """Spec to use user input passed in at config declaration.

    >>> class FooConfig(dilib.Config):
    ...     x = dilib.LocalInput(type_=str)
    ...     y = dilib.LocalInput(type_=int, default=1)

    >>> class BarConfig(dilib.Config):
    ...     foo_config = FooConfig(x="abc", y=123)

    >>> config = dilib.get_config(BarConfig)
    >>> container = dilib.get_container(config)

    >>> container.config.foo_config.x
    'abc'

    >>> container.config.foo_config.y
    123

    Args:
        type_: Expected type of input, for both static and runtime check.
        default: Default value if no input is provided.
    """
    # Cast because the return type will act like a `T`.
    return cast(T, _LocalInput(type_=type_, default=default))


class _Callable(Spec[T]):
    """Represents callable (e.g., func, type) to be called with given args."""

    _INTERNAL_FIELDS = Spec._INTERNAL_FIELDS + [
        "func_or_type",
        "args",
        "lazy_kwargs",
        "kwargs",
    ]

    def __init__(
        self,
        func_or_type: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> None:
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
            # Non-type callable (e.g., function, functor).
            return self.func_or_type(*self.args, **self.kwargs)

    def copy_with(self, *args: Any, **kwargs: Any) -> Self:
        """Make a copy with replaced args.

        Used to replace arg specs with materialized args.
        """
        return self.__class__(self.func_or_type, *args, **kwargs)


class _Prototype(_Callable[T]):
    pass


# noinspection PyPep8Naming
def Prototype(  # noqa: N802
    func_or_type: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    """Spec to call with args and no caching.

    Can be used with anything callable, including types and functions.

    >>> class Foo:
    ...     def __init__(self, x: int) -> None:
    ...         self.x = x

    >>> class FooConfig(dilib.Config):
    ...     foo = dilib.Prototype(Foo, x=1)

    >>> config = dilib.get_config(FooConfig)
    >>> container = dilib.get_container(config)
    >>> assert container.config.foo is not container.config.foo
    """
    # Cast because the return type will act like a `T`.
    return cast(T, _Prototype(func_or_type, *args, **kwargs))


def _identity(obj: T) -> T:
    return obj


def _union_dict_and_kwargs(
    values: dict[str, Any], **kwargs: Any
) -> dict[str, Any]:
    new_values = values.copy()
    new_values.update(**kwargs)
    return new_values


# noinspection PyPep8Naming
def Forward(obj: T) -> T:  # noqa: N802
    """Spec to simply forward to other spec.

    Often useful as a switch to dispatch to other specs.

    >>> class FooConfig(dilib.Config):
    ...     x0 = dilib.Object(1)
    ...     x1 = dilib.Object(2)
    ...     x = dilib.Forward(x0)

    >>> config = dilib.get_config(FooConfig)
    >>> container = dilib.get_container(config)
    >>> container.config.x
    1

    The switch can be perturbed like:

    >>> config = dilib.get_config(FooConfig)
    >>> config.x = dilib.Forward(config.x1)
    >>> container = dilib.get_container(config)
    >>> container.config.x
    2
    """
    # Cast because the return type will act like a `T`.
    return cast(T, _Prototype(_identity, obj))


class _Singleton(_Callable[T]):
    pass


# noinspection PyPep8Naming
def Singleton(  # noqa: N802
    func_or_type: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> T:
    """Spec to call with args and caching per config field.

    Can be used with anything callable, including types and functions.

    >>> class Foo:
    ...     def __init__(self, x: int) -> None:
    ...         self.x = x

    >>> class FooConfig(dilib.Config):
    ...     foo = dilib.Singleton(Foo, x=1)

    >>> config = dilib.get_config(FooConfig)
    >>> container = dilib.get_container(config)
    >>> assert container.config.foo is container.config.foo
    """
    # Cast because the return type will act like a `T`.
    return cast(T, _Singleton(func_or_type, *args, **kwargs))


# noinspection PyPep8Naming
def SingletonTuple(*args: T) -> tuple[T]:  # noqa: N802
    """Spec to create tuple with args and caching per config field.

    >>> class FooConfig(dilib.Config):
    ...     x = dilib.Object(1)
    ...     y = dilib.Object(2)
    ...     values = dilib.SingletonTuple(x, y)
    """
    # Cast because the return type will act like a tuple of `T`.
    return cast("tuple[T]", _Singleton(tuple, args))


# noinspection PyPep8Naming
def SingletonList(*args: T) -> list[T]:  # noqa: N802
    """Spec to create list with args and caching per config field.

    >>> class FooConfig(dilib.Config):
    ...     x = dilib.Object(1)
    ...     y = dilib.Object(2)
    ...     values = dilib.SingletonList(x, y)
    """
    # Cast because the return type will act like a list of `T`.
    return cast("list[T]", _Singleton(list, args))


# noinspection PyPep8Naming
def SingletonDict(  # noqa: N802
    values: dict[Any, T] | None = None, /, **kwargs: T
) -> dict[Any, T]:
    """Spec to create dict with args and caching per config field.

    Can specify either by pointing to a dict, passing in kwargs,
    or unioning both.

    >>> class FooConfig(dilib.Config):
    ...     x = dilib.Object(1)
    ...     y = dilib.Object(2)
    ...     values = dilib.SingletonDict(x=x, y=y)
    ...     # Equivalent to:
    ...     also_values = dilib.SingletonDict({"x": x, "y": y})
    """
    if values is None:
        # Cast because the return type will act like a dict of `T`.
        return cast("dict[Any, T]", _Singleton(dict, **kwargs))
    else:
        # Cast because the return type will act like a dict of `T`.
        return cast(
            "dict[Any, T]",
            _Singleton(_union_dict_and_kwargs, values, **kwargs),
        )


@contextlib.contextmanager
def config_context() -> Generator[None, None, None]:
    """Enable delayed mode for `PrototypeMixin` and `SingletonMixin`.

    >>> class Foo(dilib.SingletonMixin):
    ...     def __init__(self, x: int) -> None:
    ...         self.x = x

    >>> with dilib.config_context():
    ...     class FooConfig(dilib.Config):
    ...         foo = Foo(x=1)
    """
    global MATERIALIZE
    MATERIALIZE = False
    yield
    MATERIALIZE = True


class PrototypeMixin:
    """Helper class for `Prototype` to ease syntax in `Config`.

    Equivalent to `dilib.Prototype(cls, ...)`.

    See:
        * :class:`Prototype`
        * :func:`config_context`
    """

    def __new__(cls: type[Any], *args: Any, **kwargs: Any) -> Any:
        if MATERIALIZE:
            # noinspection PyTypeChecker
            return super().__new__(cls)
        else:
            return Prototype(cls, *args, **kwargs)


class SingletonMixin:
    """Helper class for `Singleton` to ease syntax in `Config`.

    Equivalent to `dilib.Singleton(cls, ...)`.

    See:
        * :class:`Singleton`
        * :func:`config_context`
    """

    def __new__(cls: type[Any], *args: Any, **kwargs: Any) -> Any:
        if MATERIALIZE:
            # noinspection PyTypeChecker
            return super().__new__(cls)
        else:
            return Singleton(cls, *args, **kwargs)

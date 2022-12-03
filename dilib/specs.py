from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type, Union

MISSING = object()
MISSING_DICT: Dict = {}
SpecID = int


def instantiate(cls: type, *args, **kwargs) -> Any:
    """Instantiate obj from Spec parts."""
    obj: Any = object.__new__(cls)
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


class Spec:
    """Represents delayed obj to be instantiated later."""

    NEXT_SPEC_ID = 0

    def __init__(self):
        self.spec_id = self._get_next_spec_id()

    def __getattr__(self, attr: str) -> AttrFuture:
        return AttrFuture(self.spec_id, [attr])

    # For mypy
    def __call__(self, *args, **kwargs):
        return None

    @staticmethod
    def _get_next_spec_id() -> SpecID:
        result = Spec.NEXT_SPEC_ID
        Spec.NEXT_SPEC_ID += 1
        return result


class Object(Spec):
    """Represents fully-instantiated obj."""

    def __init__(self, obj: Any):
        super().__init__()
        self.obj = obj


class Input(Spec):
    """Represents global input that can be set while getting Config."""

    def __init__(self, type_: Optional[Type] = None, default: Any = MISSING):
        super().__init__()
        self.type_ = type_
        self.default = default


class GlobalInput(Input):
    pass


class LocalInput(Input):
    pass


class Prototype(Spec):
    """Represents obj to be instantiated at every Container get call."""

    def __init__(self, cls: Union[Type, Callable], *args, **kwargs):
        super().__init__()
        self.cls = cls
        self.args = args
        self.lazy_kwargs = kwargs.pop("__lazy_kwargs", None)
        self.kwargs = kwargs

    def instantiate(self) -> Any:
        """Instantiate, useful when using outside DI framework."""
        if isinstance(self.cls, type):
            return instantiate(self.cls, *self.args, **self.kwargs)
        else:
            # Non-type callable (e.g., function, functor)
            return self.cls(*self.args, **self.kwargs)

    def copy_with(self, *args, **kwargs) -> Prototype:
        return self.__class__(self.cls, *args, **kwargs)


class PrototypeIdentity(Prototype):
    """Represents forwarding to another spec."""

    def __init__(self, obj: Any):
        super().__init__(lambda obj_: obj_, obj)

    def copy_with(self, *args, **kwargs) -> PrototypeIdentity:
        return self.__class__(*args, **kwargs)


Forward = PrototypeIdentity


class Singleton(Prototype):
    """Represents obj to be instantiated once per key per Container."""

    pass


class SingletonCollection(Singleton):
    """Represents collection to be instantiated once per key per Container."""

    def copy_with(self, *args, **kwargs) -> SingletonCollection:
        return self.__class__(*args, **kwargs)


class SingletonTuple(SingletonCollection):
    """Represents tuple to be instantiated once per key per Container."""

    def __init__(self, *args):
        super().__init__(lambda *args_: args_, *args)


class SingletonList(SingletonCollection):
    """Represents list to be instantiated once per key per Container."""

    def __init__(self, *args):
        super().__init__(lambda *args_: list(args_), *args)


class SingletonDict(SingletonCollection):
    """Represents dict to be instantiated once per key per Container.

    Can be used either with kwargs:

        >>> values = dilib.SingletonDict(x=x, y=y)

    Or with a dict (useful when keys are not strs):

        >>> values = dilib.SingletonDict({1: x, 2: y})
    """

    def __init__(self, values: Dict = MISSING_DICT, **kwargs):
        if values is MISSING_DICT:
            super().__init__(lambda **kwargs_: kwargs_, **kwargs)
            self._kwargs_style = True
        else:
            if kwargs:
                raise ValueError("Cannot set both values and kwargs")

            super().__init__(
                lambda values_: values_, __lazy_kwargs=dict(values_=values)
            )
            self._kwargs_style = False

    def copy_with(self, *args, **kwargs) -> SingletonCollection:
        if self._kwargs_style:
            return super().copy_with(*args, **kwargs)
        else:
            return Singleton(lambda values_: values_["values_"], kwargs)  # type: ignore  # noqa


class PrototypeMixin:
    """Helper class for Prototype to ease syntax in Config."""

    def __new__(cls: type, *args, **kwargs):
        return Prototype(cls, *args, **kwargs)


class SingletonMixin:
    """Helper class for Singleton to ease syntax in Config."""

    def __new__(cls: type, *args, **kwargs):
        return Singleton(cls, *args, **kwargs)

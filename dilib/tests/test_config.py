import dataclasses
import types
from typing import Any, Dict, List, Tuple

import pytest

import dilib
from dilib import di_config


@dataclasses.dataclass(frozen=True)
class Value:
    value: Any


@dataclasses.dataclass(frozen=True)
class Values:
    x: Any
    y: Any
    z: Any


@dataclasses.dataclass(frozen=True)
class SingletonValue(dilib.SingletonMixin):
    value: int


@dataclasses.dataclass(frozen=True)
class PrototypeValue(dilib.PrototypeMixin):
    value: int


def calc_offset(x: int, offset: int) -> int:
    return x + offset


class BasicConfigProtocol(dilib.ConfigProtocol):
    x: int = dilib.Object(1)
    y: int = dilib.Prototype(calc_offset, x, offset=1)

    foo: SingletonValue = SingletonValue(value=x)
    bar: PrototypeValue = PrototypeValue(value=y)


def test_config_spec():
    # No inputs
    assert di_config._ConfigSpec(BasicConfigProtocol) == di_config._ConfigSpec(
        BasicConfigProtocol
    )
    assert hash(di_config._ConfigSpec(BasicConfigProtocol)) == hash(
        di_config._ConfigSpec(BasicConfigProtocol)
    )

    # Basic inputs
    assert di_config._ConfigSpec(
        BasicConfigProtocol, x=1, y="hi"
    ) == di_config._ConfigSpec(BasicConfigProtocol, x=1, y="hi")
    assert di_config._ConfigSpec(
        BasicConfigProtocol, x=1, y="hi"
    ) != di_config._ConfigSpec(BasicConfigProtocol)

    assert hash(
        di_config._ConfigSpec(BasicConfigProtocol, x=1, y="hi")
    ) == hash(di_config._ConfigSpec(BasicConfigProtocol, x=1, y="hi"))
    assert hash(
        di_config._ConfigSpec(BasicConfigProtocol, x=1, y="hi")
    ) != hash(di_config._ConfigSpec(BasicConfigProtocol))


def test_basic() -> None:
    config = dilib.get_config(BasicConfigProtocol)

    assert config.x.obj == 1
    assert isinstance(config.y.cls, types.LambdaType)
    assert config.foo.cls is SingletonValue
    assert config.bar.cls is PrototypeValue


def test_perturb_basic() -> None:
    config0 = dilib.get_config(BasicConfigProtocol)

    config0.x = 2
    # This doesn't work well with type checkers, but the user shouldn't
    # be doing this anyway--this is only for testing.
    # noinspection PyUnresolvedReferences
    assert config0.x.obj == 2  # type: ignore

    # No class-level interactions
    config1 = dilib.get_config(BasicConfigProtocol)

    assert config1.x.obj == 1


def test_perturb_after_freeze() -> None:
    config = dilib.get_config(BasicConfigProtocol)

    config.freeze()
    with pytest.raises(dilib.FrozenConfigError):
        config.x = 100


def test_add_key_after_load() -> None:
    config = dilib.get_config(BasicConfigProtocol)

    with pytest.raises(dilib.NewKeyConfigError):
        config.new_x = 100


class ParentConfigProtocol0(dilib.ConfigProtocol):
    basic_config: BasicConfigProtocol = dilib.ConfigSpec(BasicConfigProtocol)

    baz0: SingletonValue = SingletonValue(basic_config.x)


class ParentConfigProtocol1(dilib.ConfigProtocol):
    basic_config: BasicConfigProtocol = dilib.ConfigSpec(BasicConfigProtocol)

    baz1: SingletonValue = SingletonValue(basic_config.x)
    some_str1: str = dilib.Object("abc")


class GrandParentConfigProtocol(dilib.ConfigProtocol):
    parent_config0: ParentConfigProtocol0 = dilib.ConfigSpec(
        ParentConfigProtocol0
    )
    parent_config1: ParentConfigProtocol1 = dilib.ConfigSpec(
        ParentConfigProtocol1
    )

    foobar: SingletonValue = SingletonValue(parent_config0.basic_config.x)
    some_str0: str = dilib.Object("hi")


def test_dir() -> None:
    config = dilib.get_config(GrandParentConfigProtocol)

    assert dir(config) == [
        "foobar",
        "parent_config0",
        "parent_config1",
        "some_str0",
    ]
    assert dir(config.parent_config0) == ["basic_config", "baz0"]


def test_nested_config() -> None:
    config = dilib.get_config(GrandParentConfigProtocol)

    assert id(config.parent_config0.basic_config) == id(
        config.parent_config1.basic_config
    )


# FIXME: Perturbations don't pass type checker
def test_perturb_nested_config_attrs() -> None:
    config = dilib.get_config(GrandParentConfigProtocol)

    config.some_str0 = "hello"
    config.parent_config0.basic_config.x = 100  # type: ignore
    config.parent_config1.some_str1 = "def"  # type: ignore

    # noinspection PyUnresolvedReferences
    assert config.some_str0.obj == "hello"  # type: ignore
    assert config.parent_config1.basic_config.x.obj == 100
    # noinspection PyUnresolvedReferences
    assert config.parent_config1.some_str1.obj == "def"  # type: ignore


def test_perturb_nested_config_strs() -> None:
    config = dilib.get_config(GrandParentConfigProtocol)

    config["some_str0"] = "hello"
    config["parent_config0.basic_config.x"] = 100
    config["parent_config1.some_str1"] = "def"

    assert config["some_str0"].obj == "hello"
    assert config["parent_config1.basic_config.x.obj"] == 100
    assert config["parent_config1.some_str1"].obj == "def"


def test_perturb_nested_child_config() -> None:
    config = dilib.get_config(GrandParentConfigProtocol)

    with pytest.raises(dilib.SetChildConfigError):
        config.parent_config0 = dilib.get_config(ParentConfigProtocol1)


class InputConfigProtocol0(dilib.ConfigProtocol):
    name: str = dilib.GlobalInput(str)
    context: str = dilib.GlobalInput(str, default="default")
    x: int = dilib.LocalInput(int)


class InputConfigProtocol1(dilib.ConfigProtocol):
    input_config0: InputConfigProtocol0 = dilib.ConfigSpec(
        InputConfigProtocol0, x=1
    )

    y: int = dilib.Prototype(calc_offset, input_config0.x, offset=1)


class BadInputConfigProtocol(dilib.ConfigProtocol):
    # Note missing inputs
    input_config0 = dilib.ConfigSpec(InputConfigProtocol0)


def test_input_config() -> None:
    with pytest.raises(dilib.InputConfigError):
        dilib.get_config(InputConfigProtocol1)

    with pytest.raises(dilib.InputConfigError):
        dilib.get_config(InputConfigProtocol1, name=1)

    with pytest.raises(dilib.InputConfigError):
        dilib.get_config(BadInputConfigProtocol, name="hi")

    config = dilib.get_config(InputConfigProtocol1, name="hi")

    assert config.input_config0.name.obj == "hi"
    assert config.input_config0.context.obj == "default"
    assert config.input_config0.x.obj == 1


class CollectionConfigProtocol(dilib.ConfigProtocol):
    x: int = dilib.Object(1)
    y: int = dilib.Object(2)

    foo_tuple: Tuple[int, int] = dilib.SingletonTuple(x, y)
    foo_list: List[int] = dilib.SingletonList(x, y)
    foo_dict: Dict[str, int] = dilib.SingletonDict(x=x, y=y)


class AnonymousConfigProtocol(dilib.ConfigProtocol):
    x: Value = dilib.Singleton(Value, 1)
    y: Value = dilib.Singleton(Value, dilib.Singleton(Value, x))
    z: Value = dilib.Singleton(Value, dilib.Prototype(Value, x))


class WrapperConfigProtocol(dilib.ConfigProtocol):
    _value: Value = dilib.Singleton(Value, 1)
    value: Value = dilib.Singleton(Value, _value)


class ForwardConfigProtocol(dilib.ConfigProtocol):
    other_config: GrandParentConfigProtocol = dilib.ConfigSpec(
        GrandParentConfigProtocol
    )

    x: int = dilib.Forward(other_config.parent_config0.basic_config.x)
    x_value: Value = dilib.Singleton(Value, value=x)

    foo: SingletonValue = dilib.Forward(
        other_config.parent_config0.basic_config.foo
    )
    foo_value: Value = dilib.Singleton(Value, value=foo)


class PartialKwargsConfigProtocol(dilib.ConfigProtocol):
    x: int = dilib.Object(1)
    y: int = dilib.Object(2)

    partial_kwargs: Dict[str, int] = dict(x=x, y=y)

    values: Values = dilib.Singleton(Values, z=x, **partial_kwargs)


def test_extra_global_inputs() -> None:
    with pytest.raises(dilib.InputConfigError):
        try:
            dilib.get_config(InputConfigProtocol1, name="testing", foobar=123)
        except dilib.InputConfigError as exc:
            assert "extra" in str(exc) and "'foobar'" in str(exc)
            raise


class InputConfigProtocolWithCollision(dilib.ConfigProtocol):
    input_config0: InputConfigProtocol0 = dilib.ConfigSpec(
        InputConfigProtocol0, x=1
    )

    # "name" collides with input_config0.name
    name: str = dilib.GlobalInput(str)


def test_global_input_collisions() -> None:
    with pytest.raises(dilib.InputConfigError):
        try:
            dilib.get_config(InputConfigProtocolWithCollision, name="testing")
        except dilib.InputConfigError as exc:
            assert "collision" in str(exc) and "'name'" in str(exc)
            raise

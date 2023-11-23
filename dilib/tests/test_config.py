# mypy: disable-error-code="comparison-overlap"
from __future__ import annotations

import dataclasses
import types
from typing import Any, TypeVar

import pytest

import dilib
import dilib.specs

TC = TypeVar("TC", bound=dilib.Config)


def get_config(
    config_cls: type[TC], more_type_safe: bool, **global_inputs: Any
) -> TC:
    if more_type_safe:
        return dilib.get_config(config_cls, **global_inputs)
    else:
        return config_cls().get(**global_inputs)  # type: ignore[no-any-return]


@dataclasses.dataclass(frozen=True)
class ValueWrapper:
    value: Any


@dataclasses.dataclass(frozen=True)
class ValuesWrapper:
    x: Any
    y: Any
    z: Any


@dataclasses.dataclass(frozen=True)
class SingletonValueWrapper(dilib.SingletonMixin, ValueWrapper):
    pass


@dataclasses.dataclass(frozen=True)
class PrototypeValueWrapper(dilib.PrototypeMixin, ValueWrapper):
    pass


class BasicConfig(dilib.Config):
    x = dilib.Object(1)
    y: int = dilib.Prototype(lambda x, offset: x + offset, x, offset=1)

    foo = SingletonValueWrapper(value=x)
    bar = PrototypeValueWrapper(value=y)


def test_config_spec() -> None:
    # No inputs
    assert BasicConfig() == BasicConfig()
    assert hash(BasicConfig()) == hash(BasicConfig())

    # Basic inputs
    assert BasicConfig(x=1, y="hi") == BasicConfig(x=1, y="hi")
    assert BasicConfig(x=1, y="hi") != BasicConfig()

    assert hash(BasicConfig(x=1, y="hi")) == hash(BasicConfig(x=1, y="hi"))
    assert hash(BasicConfig(x=1, y="hi")) != hash(BasicConfig())


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_basic(more_type_safe: bool) -> None:
    config = get_config(BasicConfig, more_type_safe=more_type_safe)

    assert config._get_spec("x").obj == 1
    assert isinstance(config._get_spec("y").func_or_type, types.LambdaType)
    assert config._get_spec("foo").func_or_type is SingletonValueWrapper
    assert config._get_spec("bar").func_or_type is PrototypeValueWrapper


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_perturb_basic(more_type_safe: bool) -> None:
    config0: BasicConfig = get_config(
        BasicConfig, more_type_safe=more_type_safe
    )

    config0.x = 2
    spec_x = config0._get_spec("x")
    assert isinstance(spec_x, dilib.specs._Object)
    assert spec_x.obj == 2

    # Note that there are no class-level interactions, so if we
    # create a new instance, it doesn't have prior perturbations
    config1 = dilib.get_config(BasicConfig)

    assert config1._get_spec("x").obj == 1


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_perturb_after_freeze(more_type_safe: bool) -> None:
    config = get_config(BasicConfig, more_type_safe=more_type_safe)

    config.freeze()
    with pytest.raises(dilib.FrozenConfigError):
        config.x = 100


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_add_key_after_load(more_type_safe: bool) -> None:
    config = get_config(BasicConfig, more_type_safe=more_type_safe)

    with pytest.raises(dilib.NewKeyConfigError):
        config.new_x = 100


class ParentConfig0(dilib.Config):
    basic_config = BasicConfig()

    baz0 = SingletonValueWrapper(basic_config.x)


class ParentConfig1(dilib.Config):
    basic_config = BasicConfig()

    baz1 = SingletonValueWrapper(basic_config.x)
    some_str1 = dilib.Object("abc")


class GrandParentConfig(dilib.Config):
    parent_config0 = ParentConfig0()
    parent_config1 = ParentConfig1()

    foobar = SingletonValueWrapper(parent_config0.basic_config.x)
    some_str0 = dilib.Object("hi")


class ErrorGrandParentConfig(dilib.Config):
    parent_config0 = ParentConfig0()
    parent_config1 = ParentConfig1()

    # This is pointing to a non-existent attr, so we will fail when
    # trying to get foobar via the container.
    foobar = dilib.Forward(parent_config0.non_existent_field)


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_dir(more_type_safe: bool) -> None:
    config = get_config(GrandParentConfig, more_type_safe=more_type_safe)

    assert dir(config) == [
        "foobar",
        "parent_config0",
        "parent_config1",
        "some_str0",
    ]
    assert dir(config.parent_config0) == ["basic_config", "baz0"]


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_nested_config(more_type_safe: bool) -> None:
    config = get_config(GrandParentConfig, more_type_safe=more_type_safe)

    assert id(config.parent_config0.basic_config) == id(
        config.parent_config1.basic_config
    )


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_perturb_nested_config_attrs(more_type_safe: bool) -> None:
    config = get_config(GrandParentConfig, more_type_safe=more_type_safe)

    config.some_str0 = "hello"
    config.parent_config0.basic_config.x = 100
    config.parent_config1.some_str1 = "def"

    assert config._get_spec("some_str0").obj == "hello"
    assert config.parent_config1.basic_config._get_spec("x").obj == 100
    assert config.parent_config1._get_spec("some_str1").obj == "def"


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_perturb_nested_config_strs(more_type_safe: bool) -> None:
    config = get_config(GrandParentConfig, more_type_safe=more_type_safe)

    config["some_str0"] = "hello"
    config["parent_config0.basic_config.x"] = 100
    config["parent_config1.some_str1"] = "def"

    assert config["some_str0"].obj == "hello"
    assert config["parent_config1.basic_config.x.obj"] == 100
    assert config["parent_config1.some_str1"].obj == "def"


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_perturb_nested_child_config(more_type_safe: bool) -> None:
    config = get_config(GrandParentConfig, more_type_safe=more_type_safe)

    with pytest.raises(dilib.SetChildConfigError):
        config.parent_config0 = ParentConfig1()  # type: ignore


class InputConfig0(dilib.Config):
    name = dilib.GlobalInput(str)
    context = dilib.GlobalInput(str, default="default")
    x = dilib.LocalInput(int)


class InputConfig1(dilib.Config):
    input_config0 = InputConfig0(x=1)

    y = dilib.Prototype(
        lambda x, offset: x + offset, input_config0.x, offset=1
    )


class BadInputConfig(dilib.Config):
    input_config0 = InputConfig0()  # Note missing inputs


@pytest.mark.parametrize("more_type_safe", [True, False])
def test_input_config(more_type_safe: bool) -> None:
    with pytest.raises(dilib.InputConfigError):
        InputConfig1().get()

    with pytest.raises(dilib.InputConfigError):
        InputConfig1().get(name=1)

    with pytest.raises(dilib.InputConfigError):
        BadInputConfig().get(name="hi")

    config = get_config(InputConfig1, name="hi", more_type_safe=more_type_safe)

    assert config.input_config0._get_spec("name").obj == "hi"
    assert config.input_config0._get_spec("context").obj == "default"
    assert config.input_config0._get_spec("x").obj == 1


class CollectionConfig(dilib.Config):
    x = dilib.Object(1)
    y = dilib.Object(2)
    z = dilib.Object(3)

    foo_tuple: tuple[int] = dilib.SingletonTuple(x, y)
    foo_list: list[int] = dilib.SingletonList(x, y)
    foo_dict_kwargs: dict[str, int] = dilib.SingletonDict(x=x, y=y)
    foo_dict_values0: dict[int, int] = dilib.SingletonDict({1: x, 2: y})
    foo_dict_values1: dict[str, int] = dilib.SingletonDict(values=x)
    foo_dict_values2: dict[str, int] = dilib.SingletonDict(
        {"x": x, "y": y}, z=z
    )

    # Check that untyped values don't trigger mypy errors
    _untyped_foo_tuple = dilib.SingletonTuple(x, y)
    _untyped_foo_list = dilib.SingletonList(x, y)
    _untyped_foo_dict_kwargs = dilib.SingletonDict(x=x, y=y)
    _untyped_foo_dict_values0: dict[int, int] = dilib.SingletonDict(
        {1: x, 2: y}
    )


class AnonymousConfig(dilib.Config):
    x = dilib.Singleton(ValueWrapper, 1)
    y = dilib.Singleton(ValueWrapper, dilib.Singleton(ValueWrapper, x))
    z = dilib.Singleton(ValueWrapper, dilib.Prototype(ValueWrapper, x))


class WrapperConfig(dilib.Config):
    _value = dilib.Singleton(ValueWrapper, 1)
    value = dilib.Singleton(ValueWrapper, _value)


class ForwardConfig(dilib.Config):
    other_config = GrandParentConfig()

    x = dilib.Forward(other_config.parent_config0.basic_config.x)
    x_value = dilib.Singleton(ValueWrapper, value=x)

    foo = dilib.Forward(other_config.parent_config0.basic_config.foo)
    foo_value = dilib.Singleton(ValueWrapper, value=foo)


class PartialKwargsConfig(dilib.Config):
    x = dilib.Object(1)
    y = dilib.Object(2)

    partial_kwargs = dilib.SingletonDict(x=x, y=y)

    values = dilib.Singleton(  # type: ignore[call-arg]
        ValuesWrapper,
        z=x,
        __lazy_kwargs=partial_kwargs,  # pyright: ignore
    )


class PartialKwargsOtherConfig(dilib.Config):
    partial_kwargs_config = PartialKwargsConfig()

    z = dilib.Object(3)
    values = dilib.Singleton(  # type: ignore[call-arg]
        ValuesWrapper,
        z=z,
        __lazy_kwargs=partial_kwargs_config.partial_kwargs,  # pyright: ignore
    )


def test_extra_global_inputs() -> None:
    with pytest.raises(dilib.InputConfigError):
        try:
            InputConfig1().get(name="testing", foobar=123)
        except dilib.InputConfigError as exc:
            assert "extra" in str(exc) and "'foobar'" in str(exc)
            raise


class InputConfigWithCollision(dilib.Config):
    input_config0 = InputConfig0(x=1)

    # "name" collides with input_config0.name
    name = dilib.GlobalInput(str)


def test_global_input_collisions() -> None:
    with pytest.raises(dilib.InputConfigError):
        try:
            InputConfigWithCollision().get(name="testing")
        except dilib.InputConfigError as exc:
            assert "collision" in str(exc) and "'name'" in str(exc)
            raise


def test_typing() -> None:
    # Would trigger mypy error:
    # cfg0: ParentConfig1 = dilib.get_config(ParentConfig0)

    cfg0: ParentConfig1 = dilib.get_config(ParentConfig1)

    # Would trigger mypy error:
    # _0: str = cfg0.basic_config.x

    _0: int = cfg0.basic_config.x  # noqa: F841
    _1: int = cfg0.basic_config.y  # noqa: F841

import types
from typing import Any

import pytest

import dilib


class Value:
    def __init__(self, value: Any):
        self.value = value


class Values:
    def __init__(self, x: Any, y: Any, z: Any):
        self.x = x
        self.y = y
        self.z = z


class SingletonValue(dilib.SingletonMixin):
    def __init__(self, value: int):
        self.value = value


class PrototypeValue(dilib.PrototypeMixin):
    def __init__(self, value: int):
        self.value = value


# noinspection PyTypeChecker
class BasicConfig(dilib.Config):

    x = dilib.Object(1)
    y = dilib.Prototype(lambda x, offset: x + offset, x, offset=1)

    foo = SingletonValue(value=x)  # type: ignore
    bar = PrototypeValue(value=y)  # type: ignore


def test_config_spec():
    # No inputs
    assert BasicConfig() == BasicConfig()
    assert hash(BasicConfig()) == hash(BasicConfig())

    # Basic inputs
    assert BasicConfig(x=1, y="hi") == BasicConfig(x=1, y="hi")
    assert BasicConfig(x=1, y="hi") != BasicConfig()

    assert hash(BasicConfig(x=1, y="hi")) == hash(BasicConfig(x=1, y="hi"))
    assert hash(BasicConfig(x=1, y="hi")) != hash(BasicConfig())


def test_basic():
    config = BasicConfig().get()

    assert config.x.obj == 1
    assert isinstance(config.y.cls, types.LambdaType)
    assert config.foo.cls is SingletonValue  # noqa
    assert config.bar.cls is PrototypeValue  # noqa


def test_perturb_basic():
    config0 = BasicConfig().get()

    config0.x = 2
    assert config0.x.obj == 2  # type: ignore

    # No class-level interactions
    config1 = BasicConfig().get()

    assert config1.x.obj == 1  # noqa


def test_perturb_after_freeze():
    config = BasicConfig().get()

    config.freeze()
    with pytest.raises(dilib.FrozenConfigError):
        config.x = 100


def test_add_key_after_load():
    config = BasicConfig().get()

    with pytest.raises(dilib.NewKeyConfigError):
        config.new_x = 100


# noinspection PyTypeChecker
class ParentConfig0(dilib.Config):

    basic_config = BasicConfig()

    baz0 = SingletonValue(basic_config.x)  # type: ignore


# noinspection PyTypeChecker
class ParentConfig1(dilib.Config):

    basic_config = BasicConfig()

    baz1 = SingletonValue(basic_config.x)  # type: ignore
    some_str1 = dilib.Object("abc")


# noinspection PyTypeChecker
class GrandParentConfig(dilib.Config):

    parent_config0 = ParentConfig0()
    parent_config1 = ParentConfig1()

    foobar = SingletonValue(parent_config0.basic_config.x)  # type: ignore
    some_str0 = dilib.Object("hi")


# noinspection PyTypeChecker
class ErrorGrandParentConfig(dilib.Config):

    parent_config0 = ParentConfig0()
    parent_config1 = ParentConfig1()

    # This is pointing to a non-existent attr, so we will fail when
    # trying to get foobar via the container.
    foobar = dilib.Forward(parent_config0.non_existent_field)


def test_dir():
    config = GrandParentConfig().get()

    assert dir(config) == [
        "foobar",
        "parent_config0",
        "parent_config1",
        "some_str0",
    ]
    assert dir(config.parent_config0) == ["basic_config", "baz0"]


def test_nested_config():
    config = GrandParentConfig().get()

    assert id(config.parent_config0.basic_config) == id(
        config.parent_config1.basic_config
    )


def test_perturb_nested_config_attrs():
    config = GrandParentConfig().get()

    config.some_str0 = "hello"
    config.parent_config0.basic_config.x = 100
    config.parent_config1.some_str1 = "def"

    # noinspection PyUnresolvedReferences
    assert config.some_str0.obj == "hello"  # type: ignore
    assert config.parent_config1.basic_config.x.obj == 100
    # noinspection PyUnresolvedReferences
    assert config.parent_config1.some_str1.obj == "def"  # type: ignore


def test_perturb_nested_config_strs():
    config = GrandParentConfig().get()

    config["some_str0"] = "hello"
    config["parent_config0.basic_config.x"] = 100
    config["parent_config1.some_str1"] = "def"

    assert config["some_str0"].obj == "hello"
    assert config["parent_config1.basic_config.x.obj"] == 100
    assert config["parent_config1.some_str1"].obj == "def"


def test_perturb_nested_child_config():
    config = GrandParentConfig().get()

    with pytest.raises(dilib.SetChildConfigError):
        config.parent_config0 = ParentConfig1()


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


def test_input_config():
    with pytest.raises(dilib.InputConfigError):
        InputConfig1().get()

    with pytest.raises(dilib.InputConfigError):
        InputConfig1().get(name=1)

    with pytest.raises(dilib.InputConfigError):
        BadInputConfig().get(name="hi")

    config = InputConfig1().get(name="hi")

    assert config.input_config0.name.obj == "hi"
    assert config.input_config0.context.obj == "default"
    assert config.input_config0.x.obj == 1


class CollectionConfig(dilib.Config):

    x = dilib.Object(1)
    y = dilib.Object(2)

    foo_tuple = dilib.SingletonTuple(x, y)
    foo_list = dilib.SingletonList(x, y)
    foo_dict_kwargs = dilib.SingletonDict(x=x, y=y)
    foo_dict_values0 = dilib.SingletonDict({1: x, 2: y})
    foo_dict_values1 = dilib.SingletonDict({"values": x})


class AnonymousConfig(dilib.Config):

    x = dilib.Singleton(Value, 1)
    y = dilib.Singleton(Value, dilib.Singleton(Value, x))
    z = dilib.Singleton(Value, dilib.Prototype(Value, x))


class WrapperConfig(dilib.Config):

    _value = dilib.Singleton(Value, 1)
    value = dilib.Singleton(Value, _value)


class ForwardConfig(dilib.Config):

    other_config = GrandParentConfig()

    x = dilib.Forward(other_config.parent_config0.basic_config.x)
    x_value = dilib.Singleton(Value, value=x)

    foo = dilib.Forward(other_config.parent_config0.basic_config.foo)
    foo_value = dilib.Singleton(Value, value=foo)


class PartialKwargsConfig(dilib.Config):

    x = dilib.Object(1)
    y = dilib.Object(2)

    partial_kwargs = dilib.SingletonDict(x=x, y=y)

    values = dilib.Singleton(Values, z=x, __lazy_kwargs=partial_kwargs)


class PartialKwargsOtherConfig(dilib.Config):

    partial_kwargs_config = PartialKwargsConfig()

    z = dilib.Object(3)
    values = dilib.Singleton(
        Values, z=z, __lazy_kwargs=partial_kwargs_config.partial_kwargs
    )


def test_extra_global_inputs():
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


def test_global_input_collisions():
    with pytest.raises(dilib.InputConfigError):
        try:
            InputConfigWithCollision().get(name="testing")
        except dilib.InputConfigError as exc:
            assert "collision" in str(exc) and "'name'" in str(exc)
            raise

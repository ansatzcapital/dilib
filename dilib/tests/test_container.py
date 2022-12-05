import pytest

import dilib
from dilib.tests import test_config


def test_basic():
    config = test_config.BasicConfig().get()
    container = dilib.Container(config)

    assert container.x == 1
    assert container.y == 2
    assert isinstance(container.foo, test_config.SingletonValue)
    assert container.foo.value == 1
    assert isinstance(container.bar, test_config.PrototypeValue)
    assert container.bar.value == 2

    assert container.foo is container.foo  # foo is a Singleton
    assert container.bar is not container.bar  # foo is a Prototype


def test_perturb_basic():
    config = test_config.BasicConfig().get()
    config.x = 2

    container = dilib.Container(config)
    assert container.y == 3
    assert container.foo.value == 2
    assert container.bar.value == 3


def test_get_nested():
    config = test_config.GrandParentConfig().get()
    container = dilib.Container(config)

    assert container.parent_config0.basic_config.x == 1
    assert container["parent_config0.basic_config.x"] == 1


def test_dir():
    config = test_config.GrandParentConfig().get()
    container = dilib.Container(config)

    assert dir(container) == [
        "foobar",
        "parent_config0",
        "parent_config1",
        "some_str0",
    ]
    assert dir(container.parent_config0) == ["basic_config", "baz0"]


def test_perturb_nested():
    config = test_config.GrandParentConfig().get()
    config.parent_config0.basic_config.x = 10

    container = dilib.Container(config)

    assert container.parent_config0.basic_config.x == 10
    assert container.parent_config0.basic_config.foo.value == 10
    assert container.parent_config0.basic_config.bar.value == 11
    assert (
        container.parent_config0.basic_config.foo
        is container.parent_config1.basic_config.foo
    )
    assert container.parent_config0.baz0.value == 10
    assert container.parent_config1.baz1.value == 10
    assert container.foobar.value == 10


def test_nested_keyerror():
    config = test_config.ErrorGrandParentConfig().get()
    container = dilib.Container(config)

    with pytest.raises(KeyError):
        try:
            container.foobar
        except KeyError as exc:
            assert str(exc) == (
                "\"<class 'dilib.tests.test_config.ParentConfig0'>: "
                "'non_existent_field'\""
            )
            raise


def test_input_config():
    config = test_config.InputConfig1().get(name="hi")
    config.input_config0.x = 100

    container = dilib.Container(config)
    assert container.input_config0.name == "hi"
    assert container.input_config0.context == "default"
    assert container.input_config0.x == 100
    assert container.y == 101


def test_collection_config():
    config = test_config.CollectionConfig().get()
    container = dilib.Container(config)

    assert container.x == 1
    assert container.y == 2
    assert container.foo_tuple == (1, 2)
    assert container.foo_list == [1, 2]
    assert container.foo_dict_kwargs == {"x": 1, "y": 2}
    assert container.foo_dict_values0 == {1: 1, 2: 2}
    assert container.foo_dict_values1 == {"values": 1}

    assert container.foo_tuple is container.foo_tuple


def test_anonymous():
    config = test_config.AnonymousConfig().get()
    container = dilib.Container(config)

    assert container.y.value.value is container.x
    assert container.z.value.value is container.x


def test_underscore():
    config = test_config.WrapperConfig().get()
    container = dilib.Container(config)

    assert container.value.value is container._value


def test_forward():
    config = test_config.ForwardConfig().get()
    container = dilib.Container(config)

    assert (
        container.foo is container.other_config.parent_config0.basic_config.foo
    )
    assert (
        container.foo_value.value
        is container.other_config.parent_config0.basic_config.foo
    )


def test_perturb_forward():
    config = test_config.ForwardConfig().get()

    config.x = 1000

    container = dilib.Container(config)

    # Objs that depend on original x remain unperturbed, but objs
    # that depend on the forward alias are perturbed.
    assert container.other_config.parent_config0.basic_config.x == 1
    assert container.other_config.foobar.value == 1
    assert container.x == 1000
    assert container.x_value.value == 1000


def test_perturb_partial_kwargs():
    config = test_config.PartialKwargsConfig().get()

    config.x = 10
    config.y = 20

    container = dilib.Container(config)

    assert container.x == 10
    assert container.y == 20
    assert container.values.x == 10
    assert container.values.y == 20
    assert container.values.z == 10


def test_perturb_partial_kwargs_other():
    config = test_config.PartialKwargsOtherConfig().get()

    config.partial_kwargs_config.x = 10

    container = dilib.Container(config)

    assert container.partial_kwargs_config.values.x == 10
    assert container.partial_kwargs_config.values.y == 2
    assert container.partial_kwargs_config.values.z == 10

    assert container.values.x == 10
    assert container.values.y == 2
    assert container.values.z == 3


class ObjWithAttr:
    @property
    def test_attr(self) -> int:
        return 1


class ObjAttrConfig(dilib.Config):
    test_obj = dilib.Singleton(ObjWithAttr)
    test_obj_attr = dilib.Forward(test_obj.test_attr)


class NestedConfigObjAttrConfig(dilib.Config):
    cfg = ObjAttrConfig()

    test_obj = dilib.Forward(cfg.test_obj)
    test_obj_attr = dilib.Forward(cfg.test_obj_attr)


def test_obj_attr():
    config = ObjAttrConfig().get()
    container = dilib.Container(config)

    assert container.test_obj.test_attr == 1
    assert container.test_obj_attr == 1


def test_nested_config_obj_attr():
    config = NestedConfigObjAttrConfig().get()
    container = dilib.Container(config)

    assert container.test_obj.test_attr == 1
    assert container.test_obj_attr == 1
    assert container.test_obj is container.cfg.test_obj

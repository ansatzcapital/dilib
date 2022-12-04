from typing import Type

import pytest

import dilib
from dilib.tests import test_config


def test_basic() -> None:
    config = dilib.get_config(test_config.BasicConfigProtocol)
    container = dilib.get_container(config)

    assert container.config.x == 1
    assert container.config.y == 2
    assert isinstance(container.config.foo, test_config.SingletonValue)
    assert container.config.foo.value == 1
    assert isinstance(container.config.bar, test_config.PrototypeValue)
    assert container.config.bar.value == 2

    assert container.config.foo is container.config.foo  # foo is a Singleton
    assert (
        container.config.bar is not container.config.bar
    )  # foo is a Prototype


def test_perturb_basic() -> None:
    config = dilib.get_config(test_config.BasicConfigProtocol)
    config.x = 2

    container = dilib.get_container(config)
    assert container.config.y == 3
    assert container.config.foo.value == 2
    assert container.config.bar.value == 3


def test_get_nested() -> None:
    config = dilib.get_config(test_config.GrandParentConfigProtocol)
    container = dilib.get_container(config)

    assert container.config.parent_config0.basic_config.x == 1
    assert container["parent_config0.basic_config.x"] == 1


def test_dir() -> None:
    config = dilib.get_config(test_config.GrandParentConfigProtocol)
    container = dilib.get_container(config)

    assert dir(container.config) == [
        "foobar",
        "parent_config0",
        "parent_config1",
        "some_str0",
    ]
    assert dir(container.config.parent_config0) == ["basic_config", "baz0"]


def test_perturb_nested() -> None:
    config = dilib.get_config(test_config.GrandParentConfigProtocol)

    # FIXME: Perturbations don't pass type checker
    config.parent_config0.basic_config.x = 10  # type: ignore

    container = dilib.Container(config)

    assert container.config.parent_config0.basic_config.x == 10
    assert container.config.parent_config0.basic_config.foo.value == 10
    assert container.config.parent_config0.basic_config.bar.value == 11
    assert (
        container.config.parent_config0.basic_config.foo
        is container.config.parent_config1.basic_config.foo
    )
    assert container.config.parent_config0.baz0.value == 10
    assert container.config.parent_config1.baz1.value == 10
    assert container.config.foobar.value == 10


def test_input_config() -> None:
    config = dilib.get_config(test_config.InputConfigProtocol1, name="hi")

    # FIXME: Perturbations don't pass type checker
    config.input_config0.x = 100  # type: ignore

    container = dilib.get_container(config)
    assert container.config.input_config0.name == "hi"
    assert container.config.input_config0.context == "default"
    assert container.config.input_config0.x == 100
    assert container.config.y == 101


def test_collection_config():
    config = dilib.get_config(test_config.CollectionConfigProtocol)
    container = dilib.get_container(config)

    assert container.config.x == 1
    assert container.config.y == 2
    assert container.config.foo_tuple == (1, 2)
    assert container.config.foo_list == [1, 2]
    assert container.config.foo_dict == {"x": 1, "y": 2}

    assert container.config.foo_tuple is container.config.foo_tuple


def test_anonymous() -> None:
    config = dilib.get_config(test_config.AnonymousConfigProtocol)
    container = dilib.get_container(config)

    assert container.config.y.value.value is container.config.x
    assert container.config.z.value.value is container.config.x


def test_underscore() -> None:
    config = dilib.get_config(test_config.WrapperConfigProtocol)
    container = dilib.get_container(config)

    assert container.config.value.value is container.config._value


def test_forward() -> None:
    config = dilib.get_config(test_config.ForwardConfigProtocol)
    container = dilib.get_container(config)

    assert (
        container.config.foo
        is container.config.other_config.parent_config0.basic_config.foo
    )
    assert (
        container.config.foo_value.value
        is container.config.other_config.parent_config0.basic_config.foo
    )


def test_perturb_forward() -> None:
    config = dilib.get_config(test_config.ForwardConfigProtocol)

    config.x = 1000

    container = dilib.get_container(config)

    # Objs that depend on original x remain unperturbed, but objs
    # that depend on the forward alias are perturbed.
    assert container.config.other_config.parent_config0.basic_config.x == 1
    assert container.config.other_config.foobar.value == 1
    assert container.config.x == 1000
    assert container.config.x_value.value == 1000


def test_perturb_partial_kwargs() -> None:
    config = dilib.get_config(test_config.PartialKwargsConfigProtocol)

    config.x = 10
    config.y = 20

    container = dilib.get_container(config)

    assert container.config.x == 10
    assert container.config.y == 20
    assert container.config.values.x == 10
    assert container.config.values.y == 20
    assert container.config.values.z == 10


class ObjWithAttr:
    @property
    def test_attr(self) -> int:
        return 1


class ObjAttrConfigProtocol(dilib.ConfigProtocol):
    test_obj: ObjWithAttr = dilib.Singleton(ObjWithAttr)
    test_obj_attr: int = dilib.Forward(test_obj.test_attr)


class NestedConfigObjAttrConfigProtocol(dilib.ConfigProtocol):
    cfg = dilib.ConfigSpec(ObjAttrConfigProtocol)

    test_obj = dilib.Forward(cfg.test_obj)
    test_obj_attr = dilib.Forward(cfg.test_obj_attr)


def test_obj_attr() -> None:
    config = dilib.get_config(ObjAttrConfigProtocol)
    container = dilib.get_container(config)

    assert container.config.test_obj.test_attr == 1
    assert container.config.test_obj_attr == 1


def test_nested_config_obj_attr() -> None:
    config = dilib.get_config(NestedConfigObjAttrConfigProtocol)
    container = dilib.get_container(config)

    assert container.config.test_obj.test_attr == 1
    assert container.config.test_obj_attr == 1
    assert container.config.test_obj is container.config.cfg.test_obj


class BaseCoreConfigProtocol(dilib.ConfigProtocol):
    x: int


class CoreConfigProtocol0(BaseCoreConfigProtocol):
    x: int = dilib.Object(1)


class CoreConfigProtocol1(BaseCoreConfigProtocol):
    x: int = dilib.Object(2)


class GlobalConfigInputConfigProtocol(dilib.ConfigProtocol):
    child_cfg: BaseCoreConfigProtocol = dilib.GlobalInput(
        BaseCoreConfigProtocol
    )

    y: int = dilib.Forward(child_cfg.x)


@pytest.mark.parametrize(
    "child_config_cls,perturb,expected_y",
    [
        (CoreConfigProtocol0, False, 1),
        (CoreConfigProtocol1, False, 2),
        (CoreConfigProtocol0, True, 3),
        (CoreConfigProtocol1, True, 3),
    ],
)
def test_global_config_input(
    child_config_cls: Type[BaseCoreConfigProtocol],
    perturb: bool,
    expected_y: int,
) -> None:
    config = dilib.get_config(
        GlobalConfigInputConfigProtocol, child_cfg=child_config_cls
    )

    if perturb:
        # FIXME: Perturbations don't pass type checker
        config.child_cfg.x = 3  # type: ignore

    container = dilib.get_container(config)

    assert container.config.y == expected_y


class LocalConfigInputConfigProtocol(dilib.ConfigProtocol):
    child_cfg: BaseCoreConfigProtocol = dilib.LocalInput(
        BaseCoreConfigProtocol
    )

    y: int = dilib.Forward(child_cfg.x)


@pytest.mark.parametrize(
    "child_config_cls,perturb,expected_y",
    [
        (CoreConfigProtocol0, False, 1),
        (CoreConfigProtocol1, False, 2),
        (CoreConfigProtocol0, True, 3),
        (CoreConfigProtocol1, True, 3),
    ],
)
def test_local_config_input(
    child_config_cls: Type[BaseCoreConfigProtocol],
    perturb: bool,
    expected_y: int,
) -> None:
    config = dilib.get_config(
        dilib.ConfigSpec(
            LocalConfigInputConfigProtocol, child_cfg=child_config_cls
        )
    )

    if perturb:
        # FIXME: Perturbations don't pass type checker
        config.child_cfg.x = 3  # type: ignore

    container = dilib.get_container(config)

    assert container.config.y == expected_y

import dataclasses
from typing import TypeVar

import dilib

T = TypeVar("T")


@dataclasses.dataclass(frozen=True)
class Values:
    x: int


class ConfigProtocolA(dilib.ConfigProtocol):
    x: int = dilib.Object(1)


class ConfigProtocolB(dilib.ConfigProtocol):
    cfg_a: ConfigProtocolA = dilib.ConfigSpec(ConfigProtocolA)

    values: Values = dilib.Singleton(Values, x=cfg_a.x)


def test_typing() -> None:
    config: dilib.Config[ConfigProtocolB] = dilib.get_config(ConfigProtocolB)
    ctr: dilib.Container[ConfigProtocolB] = dilib.get_container(config)

    cfg_a: ConfigProtocolA = ctr.config.cfg_a

    # NB: By annotating this test with  `-> None`, mypy will complain
    # if we, e.g., we change this to `x: str`.
    x: int = cfg_a.x
    assert x == 1

    values: Values = ctr.config.values
    assert values.x == 1

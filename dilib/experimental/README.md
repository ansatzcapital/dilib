# Experimental Alternate Syntax

## Example

TODO

## Pros/Cons over Classic Syntax

Pros

- Classic syntax is in some ways a DSL, and this syntax is
basically just a plain Python class with cached properties
- Fewer concepts and easier-to-understand names (e.g., no separation
between configs and containers, no exposed singleton/prototype/etc. specs,
no special collection specs, no mix-in hacks, no lazy kwargs,
words like `cache` instead of `Singleton`, anonymous specs are expressed
with regular Python construction).
- Although classic syntax should work entirely with static type checkers,
because we don't need to "lie" to the type checker
(e.g., `dilib.Singleton(T) -> T`), we should have much more robust
static checking across editor contexts and time
- Instead of a bag of global inputs (which can even collide),
local inputs are explicitly linked to their types,
but still easily available at the top level when creating a container

Cons

- More boilerplate code (e.g., need to style as a proper function,
can't infer type from value)

## Pros over Simple Alternative

Why not just have a container like this?

```python
@dataclasses.dataclass(frozen=True)
class FooContainer:
    bar_ctr: BarContainer

    @functools.cached_property
    def host(self) -> str:
        return "abc"
```

- Child containers get created automatically, and also once per type
(which is probably what you want to do)
- Containers understand the hierarchy of parent/child containers,
which means every object described has a globally-addressable name
("global" with respect to the root config)
    - E.g., this is useful in CLIs with flags like `--name bar_ctr.xyz`
    that allows you to pass to the root container directly
    (`foo_ctr[args.name]`)
- We maintain self-consistency guarantee under perturbing because
we don't allow users to perturb after *any* object in the container
hierarchy has retrieved a value

## Pattern: Load Config from File

```python
import json
from pathlib import Path

import cattrs
from dilib.experimental import Container, container


def load_config(value: T | str | Path, cls: type[T]) -> T:
    if isinstance(value, (str, Path)):
        converter = cattrs.Converter()
        data = json.load(Path(value).open("rb"))
        return converter.structure(data, cls)

    return value


@dataclasses.dataclass(frozen=True)
class EngineConfig:
    host: str
    port: int


@container
class EngineContainer(Container):
    input_config: EngineConfig | Path

    @cache
    def config(self) -> EngineConfig:
        return load_config(self.input_config)

    @cache
    def extra_param(self) -> int:
        return 123

    @cache
    def engine(self) -> Engine:
        return DatabaseEngine(
            self.host, self.port, extra_param=self.extra_param
        )


ctr0 = FooContainer.create(
    {EngineContainer: {"input_config": Path("config.json")}}
)
ctr1 = FooContainer.create(
    {EngineContainer: {"input_config": EngineConfig("abc", 8000)}}
)
```

## Notes

- We don't raise a runtime error on trying to set a new key on a container
when perturbing because the static type checker should pick this up.
- We no longer validate container params (the equivalent to global/local
inputs in classic). If the user wants this, they can validate
with a custom `__post_init__()` in their container class.
(Our type validation logic was never advanced enough to understand complex
types anyway.)


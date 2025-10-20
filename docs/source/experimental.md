# Experimental

New alternate syntax that's less DSL and more "regular Python classes",
inspired by writing the docs for "custom containers" in {doc}`non_lib_alts`

## Example

```{literalinclude} ../../dilib/experimental/tests/test_core.py
:language: python
:lines: 1-146
```

See `dilib/experimental/tests/test_core.py` for more.

## Anatomy of a Container

A container is now a regular [`dataclasses.dataclass(frozen=False, ...)`](https://docs.python.org/3/library/dataclasses.html)
with these types of values:

|Type|Examples from Above|Created|
|-|-|-|
|Field value|`EngineContainer.host`, `WheelContainer.tire_type`|Upon container creation (each container is created *once* per container type)|
|`@call` property value|`WheelContainer.wheel`|Upon *every* value retrieval|
|`@cache` property value|`EngineContainer.engine`, `CarContainer.car`|Upon *first* value retrieval|

- Primitives, simple, and cheap-to-construct objects can be field values
- More complex objects that need to be recreated at every retrieval
should be `@call` property values
- More complex objects that need to be created only once at first retrieval
(e.g., they're expensive to construct, they contain important state)
should be `@cache` property values

## Pros/Cons over Classic Syntax

Pros

- Classic syntax is in some ways a DSL, and this syntax is
basically just a plain Python class with cached properties
- Fewer concepts and easier-to-understand names (e.g., no separation
between configs and containers,
no exposed singleton/prototype/forward/etc. specs,
no special collection specs, no mix-in hacks, no lazy kwargs,
no `container.config` confusion, words like `cache` instead of `Singleton`,
anonymous specs are expressed with regular Python construction)
- Although classic syntax should work entirely with static type checkers,
because we don't need to "lie" to the type checker
(e.g., `dilib.Singleton(T) -> T`), we should have much more robust
static checking across editor/checker contexts and time
- Instead of a bag of global inputs (which can even collide),
local inputs are explicitly linked to their types,
but still easily available at the top level when creating a container
- Force user to consider when the container value type should be
abstract instead of concrete

Cons

- More boilerplate code. Specifically, everything needs to be a proper
Python property-style method (e.g., need to type `def ...`, can't infer
value type)

## Pros/Cons over Simpler "Custom Container" Alternative

You could implement something similar with a simpler custom container type:

```python
@dataclasses.dataclass(frozen=True)
class EngineContainer:
    common_ctr: CommonContainer
    host: str

    @functools.cached_property
    def engine(self) -> Engine:
        return DatabaseEngine(self.host)
```

Pros

- Child containers get created automatically and also once per type
(i.e., there's only ever exactly one instance of `CommonContainer`
in every parent container in which it's referenced).
We assume this is what you probably want to do. It's all the more
difficult when the number of containers increase, with overlapping
common container instances that need to be shared across parent containers.
- Containers understand the hierarchy of parent/child containers
and support dotted keys (e.g., `ctr["x.y.z"]`), which means
every object now has a globally-addressable name
("global" with respect to the root config)
    - E.g., in CLIs with flags, you can have flags like `--name bar_ctr.xyz`
    that you pass to the root container directly
    (`ctr[args.name]`)
- We maintain self-consistency guarantee under perturbing because
we don't allow users to perturb after *any* object in the container
hierarchy has retrieved a value

Cons

- Need to learn new library

## New Potential Pattern: Load Config from File

If some of your config values come from a config file (e.g., JSON, YAML, TOML),
you can use those values easily in the container:

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

    @call
    def timeout_secs(self) -> int:
        return 10

    @cache
    def engine(self) -> Engine:
        return DatabaseEngine(
            self.config.host, self.config.port, timeout_secs=self.timeout_secs
        )


ctr0 = FooContainer.create(
    {EngineContainer: {"input_config": Path("config.json")}}
)
ctr1 = FooContainer.create(
    {EngineContainer: {"input_config": EngineConfig("abc", 8000)}}
)
```

Note that, for now, if you want to perturb `ctr.config`, you'll have to provide
the entire object. But because you can't perturb a container after getting a
value from it (it's frozen on first get to guarantee self-consistency),
you won't be able to perturb just one field of the config object easily.
(Perhaps we should add a `set_with(func: Callable[[T], T])` method?)

## Notes

We no longer validate container params (the equivalent to global/local
inputs in classic). If the user wants this, they can validate
with a custom `__post_init__()` in their container class.
(Our type validation logic was never advanced enough to understand complex
types anyway.)


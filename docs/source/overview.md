# Overview

## Components

Inherit from `dilib.Config` to specify your objects and params:

```python
class FooConfig(dilib.Config):
    ...
```

Then get a perturbable config instance, passing in any required global inputs:

```python
config = dilib.get_config(FooConfig, **global_inputs)
```

Next, get the container:

```python
container = dilib.get_container(config)
```

Finally, get the objects you'd like. There are 3 ways to do so:

```python
# 1. Use `container.config.name` for statically type-safe retrieval
obj = container.config.x_config.y_config.z

# 2. Use `container.name` directly in dynamic contexts (e.g., IPython, Jupyter)
obj = container.x_config.y_config.z

# 3. Use `container[name]` when taking inputs from user (e.g., CLI)
obj = container["x_config.y_config.z"]
```

## Specs

- `dilib.Object(obj)`: Pass through already-instantiated object
- `dilib.Forward(other_spec)`: Forward to a different config field
- `dilib.Prototype(cls, *args, **kwargs)`: Instantiate a new object
(or call the function) at each container retrieval
- `dilib.Singleton(cls, *args, **kwargs)`: Instantiate a new object
(or call the function) and cache object in container
- `dilib.Singleton{Tuple,List,Dict}`: Special helpers to ease
collections of specs.

Note that `Prototype` and `Singleton` support an optional
`__lazy_kwargs` arg, which allows you to pass in a subset of the
args from a different dict spec. (This is not statically type safe,
so you will have to add a `# type: ignore` if using `mypy` and/or `pyright`.)

E.g.:

```python
import dataclasses

import dilib


@dataclasses.dataclass(frozen=True)
class ValuesWrapper:
    x: int
    y: int
    z: int = 3


class CollectionsConfig(dilib.Config):
    x = dilib.Object(1)
    y = dilib.Object(2)
    z = dilib.Object(3)

    xy_tuple = dilib.SingletonTuple(x, y)
    xy_list = dilib.SingletonList(x, y)
    xy_dict0 = dilib.SingletonDict(x=x, y=y)
    xy_dict1 = dilib.SingletonDict({"x": x, "y": y})
    xy_dict2 = dilib.SingletonDict({"x": x, "y": y}, z=z)

    # You can also build a partial kwargs dict that can be
    # re-used and combined downstream
    partial_kwargs = dilib.SingletonDict(x=x, y=y)
    values0 = dilib.Singleton(ValuesWrapper, __lazy_kwargs=partial_kwargs)
    values1 = dilib.Singleton(
        ValuesWrapper, z=4, __lazy_kwargs=partial_kwargs
    )


config = dilib.get_config(CollectionsConfig)
container = dilib.get_container(config)

assert container.config.xy_tuple == (1, 2)
assert container.config.xy_list == [1, 2]
assert container.config.xy_dict0 == {"x": 1, "y": 2}
assert container.config.xy_dict1 == {"x": 1, "y": 2}
assert container.config.xy_dict2 == {"x": 1, "y": 2, "z": 3}
```

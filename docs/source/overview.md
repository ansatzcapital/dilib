# Overview

## Components

- `dilib.Config`: Inherit from this to specify your objects and params
- `config = dilib.get_config(ConfigClass, **global_inputs)`: Instantiate
config object
- `container = dilib.get_container(config)`: Instantiate container object
by passing in the config object
- `container.config.x_config.y_config.z`: Get the instantianted object
  - Alternatively: `container.x_config.y_config.z`
  - Or via string name: `container["x_config.y_config.z"]`

## Specs

- `dilib.Object(obj)`: Pass-through already-instantiated object
- `dilib.Forward(other_spec)`: Forward to a different config field
- `dilib.Prototype(cls, *args, **kwargs)`: Instantiate a new object
(or call the function) at each container retrieval
- `dilib.Singleton(cls, *args, **kwargs)`: Instantiate a new object
(or call the function) and cache object in container
- `dilib.Singleton{Tuple,List,Dict}`: Special helpers to ease
collections of specs. E.g.:

```python
import dataclasses

import dilib


@dataclasses.dataclass(frozen=True)
class ValuesWrapper:
    x: int
    y: int
    z: int = 3


class CollectionsConfig(dilib.Config):
    x: int = dilib.Object(1)
    y: int = dilib.Object(2)
    z: int = dilib.Object(3)

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

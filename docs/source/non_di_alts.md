# Non-DI Alternatives

## Comparison

|Method|Global addressessibility|Static auto-complete & type-safety|Delayed instantation|Self-consistent perturb|
|-|-|-|-|-|
|`dict[str, Any]`|*️⃣|❌|❌|❌|
|`TypedDict`|*️⃣|✅|❌|❌|
|Text config (e.g., YAML)|✅|❌|✅|✅|
|`dataclasses`|*️⃣|✅|❌|❌|
|Global variables|*️⃣|✅|❌|❌|
|Custom containers|*️⃣|✅|✅|*️⃣|
|`dilib`|✅|✅|✅|✅|

*️⃣ Achievable with a little helper code. E.g., one could write a helper
for the `TypedDict` variant that translates `"engine_config.engine"`
to getting attrs one level at a time, much like `dilib` does.
(`"engine_config"` first, followed by `"engine"`).

## `dict[str, Any]`

```python
# Engine config/container
container["address"] = "some-db-address"
container["db_engine"] = DBEngine(container["address"])
container["mock_engine"] = MockEngine()
container["engine"] = container["engine_config"]["alt_engine"]

# Car config/container
container = {"engine_config": container}
container["car_a"] = Car(container["engine_config"]["engine"])
```

Note that there's no type safety, no auto-complete, and no delayed
instantiation.

## `TypedDict`

```python
class EngineConfig(TypedDict):
    address: str
    db_engine: DBEngine
    mock_engine: MockEngine
    engine: Engine


class CarConfig(TypedDict):
    engine_config: EngineConfig
    car: Car


address = "some-db-address"
db_engine = DBEngine(address)
engine = db_engine
engine_config = EngineConfig({
    address: address,
    db_engine: db_engine,
    mock_engine: MockEngine(),
    engine: engine,
})
car_config = CarConfig({
    "engine_config": engine_config,
    "car": Car(engine_config["engine"]),
})
```

We've gained type safety and auto-complete, but we still don't have
delayed instantiation. In addition, composing the objects and configs
is unwieldy and requires thought (e.g., for `engine` to point to the
same instance as `db_engine`, one is required to create them outside
of the dicts).

## Text config (e.g., YAML)

```yaml
engine_config:
    address: &address "some-db-address"
    db_engine: &engine
        class: "module_a.DBEngine"
        address: *address
    mock_engine:
        class: "module_b.MockEngine"
    engine: *engine
car_config:
    car: "module_c.Car"
    engine: *engine
```

Or one could handle references in Python code instead:

```yaml
engine_config:
    address: "some-db-address"
    db_engine:
        class: "module_a.DBEngine"
        address: "ref:..address"
    mock_engine:
        class: "module_b.MockEngine"
    engine: "ref:db_engine"
car_config:
    car: "module_c.Car"
    engine: "ref:..engine_config.engine"
```

## `dataclasses`

```python
@dataclasses.dataclass(frozen=True)
class EngineConfig:
    address: str
    db_engine: DBEngine
    mock_engine: MockEngine
    engine: Engine


@dataclasses.dataclass(frozen=True)
class CarConfig:
    engine_config: EngineConfig
    car: Car


# Essentially identical to `TypedDict` above
```

## Global variables

```python
address = "some-db-address"
DB_ENGINE = DBEngine(address)
MOCK_ENGINE = MockEngine()
ENGINE = DB_ENGINE

CAR = Car(ENGINE)
```

It's generally considered an anti-pattern to do a lot of work
(whether expensive compute or IO calls) at import time. In addition,
there's no way to perturb the parameters programmatically and no
way to hold multiple views of the universe of objects in the same process.

## Custom container

```python
@dataclasses.dataclass(frozen=True)
class EngineContainer:
    @functools.cached_property
    def db_engine(self) -> DBEngine:
        return DBEngine(...)

    @functools.cached_property
    def engine(self) -> Engine:
        return self.db_engine


@dataclasses.dataclass(frozen=True)
class CarContainer:
    engine_container: EngineContainer

    @functools.cached_property
    def car(self) -> Car:
        return Car(self.engine_container.engine)
```

This is very similar to the functionality provided by `dilib`!
However, it would require some more work on the part of the user.

First, if the containers are heavily nested, you have to worry
about using the same container reference in all the downstream
containers, thus creating a DI problem in a DI solution.

Second, although one could monkey-patch perturbations on the
container objects, there's no 3-step process, so you don't have a
guarantee that no objects have been instantiated when you
start perturbing. (Because if you perturb after instantiating,
you have to worry about whether the perturbed value would have created
a different object instance than the once already created.)

One could imagine creating some helpers to address some of these issues:

```python
class EngineContainer(dilib.Container):
    @dilib.singleton
    def db_engine(self) -> DBEngine:
        return DBEngine(...)

    @dilib.forward
    def engine(self) -> Engine:
        return self.db_engine


class CarContainer(dilib.Container):
    engine_container: EngineContainer

    @dilib.singleton
    def car(self) -> Car:
        return Car(self.engine_container.engine)


container = CarContainer.get()
engine = container.engine_container.engine
```

This library would have to:
* Create child containers by type in the `.get()`
* Prevent property perturbing after any object has been instantianted
in any container or its child containers
* Expose nested attribute retrieval
* Support global and local inputs

Except, at this point, you basically have `dilib` with slightly different
syntax.

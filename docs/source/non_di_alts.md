# Non-DI Alternatives

## Comparison

|Method|Global addressessibility|Static auto-complete & type-safety|Delayed instantation|Self-consistent perturb|
|-|-|-|-|-|
|`dict[str, Any]`|✅*|❌|❌|❌|
|`TypedDict`|✅*|✅|❌|❌|
|Text config (e.g., YAML)|✅|❌|✅|✅|
|`dataclasses`|✅*|✅|❌|❌|
|Global variables|✅**|✅|❌|❌|
|`dilib`|✅|✅|✅|✅|

*One would need a simple helper that recurses down attrs one level at a time.
E.g., something that would translate `"engine_config.engine"` to getting attr
`"engine_config"` first, followed by `"engine"`.

**Native Python fully-qualified name

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

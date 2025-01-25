# Tips, Patterns, and FAQs

## Factories for Dynamic Objects

If you need to configure objects dynamically
(e.g., check db value to resolve what type to use,
set config keys based on another value), consider a factory pattern like:

```python
import dataclasses

import dilib


# Object that needs to be created dynamically
@dataclasses.dataclass(frozen=True)
class Foo:
    value: int


# Factory that takes static params via constructor injection and
# dynamic params via method injection
@dataclasses.dataclass(frozen=True)
class FooFactory:
    db_host: str
    alpha: int
    beta: int

    def get_foo(self, gamma: int) -> Foo:
        raise NotImplementedError


# Object that needs Foo object
@dataclasses.dataclass(frozen=True)
class FooClient:
    foo_factory: FooFactory

    def process_foo_value(self) -> int:
        return 100 + self.foo_factory.get_foo(gamma=3).value


class FooConfig(dilib.Config):
    db_host = dilib.GlobalInput(type_=str, default="some-db-address")
    foo_factory = dilib.Singleton(
        FooFactory, db_host=db_host, alpha=1, beta=2
    )
    foo_client = dilib.Singleton(FooClient, foo_factory=foo_factory)
```

## When should I use type annotations?

TODO

## Why do I need to wrap object instantions in specs?

TODO

## What's the deal with `container.config` and config types?

TODO

## Anti-pattern: use of container inside of library code

TODO

## Forwarding pattern

TODO

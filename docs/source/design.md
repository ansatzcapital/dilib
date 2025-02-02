# Design

## Static Typing

An important constraint of the design of this framework was that both
config authors and container users should be able to statically reason
about the objects and values they're using. That is, it's important
that all `dilib` functionality is compatible with `mypy` and `pyright`
type checking, with no magic or plugins required.

## Prevent Pollution of Objects

The dependency between DI configs and actual objects in the
object graph should be one way:
the DI config depends on the object graph types and values.
This keeps the objects clean of
particular decisions made by the DI framework. It also means you
can switch DI frameworks with no changes to the objects themselves.

(`dilib` offers optional mixins that violate this decision
for users that want to favor easier syntax.
See [Easier syntax](https://ansatzcapital.github.io/dilib/latest/patterns.html#easier-syntax).)

## Child Configs are Singletons by Type

In `dilib`, when you set a child config on a config object,
you're not actually instantiating the child config
(despite what it looks like).
Rather, you're creating a spec that will be instantiated
when the root config's `.get()` is called.
This means that the config instances are singletons by *type*
(unlike the actual objects specified in the config, which are by *alias*).
It would be cleaner to create instances of common configs and
pass them through to other configs
(that's what DI is all about, after all!). However, the decision was made
to not allow this because this would make
building up configs almost as complicated as building up the
actual object graph users are interested in
(essentially, the user would be engaged in an abstract meta-DI problem).
As such, all references to the same config type are
automatically resolved to the same instance,
at the expense of some flexibility and directness.
The upside, however, is that it's much easier to create nested configs,
which means users can get to designing the actual object graph quicker.

## Scale and Config Composability

It's important that configs are naturally composable: all
configs can automatically be both root configs for certain applications
and child configs for others.

For example, an application that only cares about engines would do:

```python
def main() -> None:
    config = dilib.get_config(EngineConfig, ...)
    container = dilib.get_container(config)

    engine = container.config.engine

    # Now do something with the engine
```

But that same exact `EngineConfig` can also be nested in a `CarConfig`:

```python
class CarConfig(dilib.Config):
    engine_config = EngineConfig()
```

This means that you can scale to a large number of configs and objects
without building monolithic config objects. And the line between
configs can represent different subdomains or even teams of the project.

# Design

## Static Typing

A large constraint of the design of this framework was that the both
config authors and container users should be able to statically reason
about the objects and values they're using. That is, it's important
that all `dilib` functionality is compatible with `mypy` and `pyright`
type checking, with no magic or plugins required.

## Prevent Pollution of Objects

The dependency between the DI config and the actual objects in the
object graph should be one way:
the DI config depends on the object graph types and values.
This keeps the objects clean of
particular decisions made by the DI framework.

(`dilib` offers optional mixins that violate this decision
for users that want to favor the typing and
auto-completion benefits of using the object types directly.)

## Child Configs are Singletons by Type

In `dilib`, when you set a child config on a config object,
you're not actually instantiating the child config.
Rather, you're creating a spec that will be instantiated
when the root config's `.get()` is called.
This means that the config instances are singletons by type
(unlike the actual objects specified in the config, which are by alias).
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

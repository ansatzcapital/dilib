# Library Alternatives

As always, developers should consider carefully whether (1) DI is the
correct pattern for their needs, whether (2) the scale of the problem
requires a DI framework, and (3) which DI framework to use.

For (3), `dilib` comes with a core set of functionality that may be more
suitable for some problems. This document motivates why a new DI framework
was built and highlights some differences with existing DI frameworks,
but it's not meant to detract from the hard work and innovation of these
other libraries.

## pinject

Advantages of `dilib` over [`pinject`](https://github.com/google/pinject):

- It has been archived by the owner on Jan 10, 2023
- Focus on simplicity.
  - The syntax of `foo = dilib.Object("a")` looks more like
  regular dataclasses than `bind("foo", to_instance="a")`.
  - Child configs look like just another field on the config.
- Getting objects is via *names* rather than *classes*.
  - In `pinject`, the equivalent of container attr access
    takes a class (like `Car`) rather than a config addressess.
- No implicit wiring: No assumptions are made about aligning
arg names with config params.
  - `pinject` does have an explicit mode,
    but the framework's default state is implicit.
  - The explicit wiring in `dilib` configs obviates the need
  for complications like [inject decorators](https://github.com/google/pinject#safety)
  and [annotations](https://github.com/google/pinject#annotations).
- Minimal or no pollution of objects: Objects are not aware of
the DI framework.
  - The only exception in `dilib` is the optional [easier syntax mode](https://ansatzcapital.github.io/dilib/latest/patterns.html#easier-syntax).
  In `pinject`, on the other hand, one is required to
  decorate with `@pinject.inject()` in some circumstances.

## dependency-injector

Advantages of `dilib` over [`dependency-injector`](https://github.com/ets-labs/python-dependency-injector):

- `dilib` highly encourages static containers over dynamic ones
by not including dynamic functionality at all
- Separation between "config" and "container"
(`dependency-injector` conflates the two)
- Easy-to-use perturbing with simple `config.x = new_value` syntax
- Easier to nest configs, with same syntax as defining specs
- Child configs are strongly typed instead of relying on
`DependenciesContainer` stub
(which enables IDE auto-complete and type checking)
  - See [https://github.com/ets-labs/python-dependency-injector/issues/774](https://github.com/ets-labs/python-dependency-injector/issues/774)
- No separation between configuration and specs: they have the same
syntax and static typing capability
- Easier-to-use global input configuration
- Written in native Python for more transparency

## injector

[`injector`](https://github.com/python-injector/injector)

TODO

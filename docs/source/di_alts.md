# DI Alternatives

## pinject

Advantages of `dilib` over [`pinject`](https://github.com/google/pinject):

- It has been archived by the owner on Jan 10, 2023
- Focus on simplicity. E.g.:
  - `foo = dilib.Object("a")` rather than `bind("foo", to_instance="a")`.
  - Child configs look like just another field on the config.
- Getting is via *names* rather than *classes*.
  - In `pinject`, the equivalent of container attr access
    takes a class (like `Car`) rather than a config addressess.
- No implicit wiring: No assumptions are made about aligning
arg names with config params.
  - Granted, `pinject` does have an explicit mode,
    but the framework's default state is implicit.
  - The explicit wiring in dilib configs obviates the need
  for complications like [inject decorators](https://github.com/google/pinject#safety)
  and [annotations](https://github.com/google/pinject#annotations).
- Minimal or no pollution of objects: Objects are not aware of
the DI framework. The only exception is:
if you want the IDE autocompletion to work when wiring up configs in an
environment that does not support `ParamSpec`
(e.g., `car = Car(engine=...)`), you have
to inherit from, e.g., `dilib.SingletonMixin`. But this is completely
optional; in `pinject`, on the other hand, one is required to
decorate with `@pinject.inject()` in some circumstances.

## dependency-injector

Advantages of `dilib` over [`dependency-injector`](https://github.com/ets-labs/python-dependency-injector):

- `dilib` highly encourages static containers over dynamic ones
by not including dynamic functionality at all
- Cleaner separation between "config" and "container"
(`dependency-injector` conflates the two)
- Easy-to-use perturbing with simple `config.x = new_value` syntax
- Easier to nest configs, with same syntax as defining specs
- Child configs are strongly typed instead of relying on
`DependenciesContainer` stub
(which enables IDE auto-complete and type checking)
- No separation between configuration and specs: they have the same
syntax and static typing capability
- Easier-to-use global input configuration
- Written in native python for more transparency

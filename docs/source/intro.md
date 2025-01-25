# Intro

## About DI

[Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection)
can be thought of as a **software engineering pattern**
as well as a **framework**. The goal is to describe and instantiate objects in a more
composable, modular, and uniform way.

The **pattern** is: when creating objects, always express what you depend on,
and let someone else give you those dependencies. (This is sometimes
referred to as the "Hollywood principle": "Don't call us; we'll call you.")

The **framework** is meant to ease the inevitable boilerplate
that occurs when following this pattern, and `dilib` is one such framework.

See the [Google Clean Code Talk about Dependency Injection](https://testing.googleblog.com/2008/11/clean-code-talks-dependency-injection.html).

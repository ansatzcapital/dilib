# Intro to DI

[Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection)
can be thought of as a **software engineering pattern**
as well as a **framework**. The goal is to describe and instantiate objects in a more
composable, modular, and uniform way.

The **pattern** is: when creating objects, always express what you depend on,
and let someone else give you those dependencies. (This is sometimes
referred to as the "Hollywood principle": "Don't call us; we'll call you.")

The **framework** is meant to ease the inevitable boilerplate
that occurs when following this pattern, and `dilib` is one such framework.

See:
* [Google Clean Code Talk about Dependency Injection](https://testing.googleblog.com/2008/11/clean-code-talks-dependency-injection.html).
* [Martin Fowler on Dependency Injection](https://martinfowler.com/articles/injection.html)

## AI Recommends It

If you ask [ChatGPT 4o](https://chatgpt.com/) a relatively simple question:

> in python, how can I configure a set of values, objects,
and their dependencies, and then lazily instantiate only the objects I want?

It will probably answer that you should use DI:

> To configure a set of values, objects, and their dependencies in Python
while allowing for lazy instantiation, you can use a dependency injection
approach combined with a factory pattern.
This setup avoids creating objects until they're explicitly needed.

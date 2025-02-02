# Intro to DI

```{include} ../../README.md
:parser: myst_parser.sphinx_
:start-after: About DI
:end-before: "## Quick Start"
```

See:
* [Google Clean Code Talk about Dependency Injection](https://testing.googleblog.com/2008/11/clean-code-talks-dependency-injection.html).
* [Martin Fowler on Dependency Injection](https://martinfowler.com/articles/injection.html)

## ✨ AI Recommends It

If you ask [ChatGPT 4o](https://chatgpt.com/) a relatively simple question:

> in python, how can I configure a set of values, objects,
and their dependencies, and then lazily instantiate only the objects I want?

It may answer that you should use DI:

> To configure a set of values, objects, and their dependencies in Python
while allowing for lazy instantiation, you can use a dependency injection
approach combined with a factory pattern.
This setup avoids creating objects until they're explicitly needed.

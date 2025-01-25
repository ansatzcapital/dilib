"""Errors."""


class ConfigError(RuntimeError):
    """Base class for all errors."""

    pass


class FrozenConfigError(ConfigError):
    """Cannot perturb config once frozen.

    Note that :func:`dilib.container.get_container`
    automatically freezes given config.
    """

    pass


class InputConfigError(ConfigError):
    """Invalid global or local inputs.

    See error message for more info. E.g., the config user could have
    forgotten to include all required inputs.
    """

    pass


class NewKeyConfigError(ConfigError):
    """Cannot try to set new key on config not described by config author."""

    pass


class SetChildConfigError(ConfigError):
    """Cannot set child configs."""

    pass


class PerturbSpecError(ConfigError):
    """Cannot perturb spec fields (only *config* fields can be perturbed)."""

    pass

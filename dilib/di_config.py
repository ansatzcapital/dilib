from __future__ import annotations

import datetime
from typing import Any, Dict, Iterable, Optional, Set, Type, Union

from dilib import errors, specs, utils

PRIMITIVE_TYPES = (
    type(None),
    bool,
    int,
    float,
    str,
    datetime.date,
    datetime.time,
    datetime.datetime,
)


def check_type(
    value: Any, type_: Optional[Type] = None, tag: Optional[str] = None
):
    if type_ is None:
        return

    if hasattr(type_, "__args__"):
        # TODO! Check nested typing types here.
        return
    else:
        types = (type_,)

    if not isinstance(value, types):
        raise errors.InputConfigError(
            f"{tag} input mismatch types: {type(value)} is not {type_}"
        )


class ConfigSpec(specs.Spec):
    """Spec for Configs."""

    def __init__(self, cls: Type[Config], **kwargs):
        super().__init__()
        self.cls = cls
        self.kwargs = kwargs

    def _instantiate(self, config_locator: ConfigLocator) -> Config:
        """Instantiate, useful when using outside DI framework."""
        return specs.instantiate(self.cls, config_locator, **self.kwargs)

    def get(self, **global_inputs) -> Config:
        """Get instance of this Config."""
        config_locator = ConfigLocator(**global_inputs)
        config = config_locator.get(self)

        # noinspection PyProtectedMember
        global_input_keys = config._get_all_global_input_keys()
        extra_global_input_keys = set(global_inputs.keys()) - global_input_keys
        if extra_global_input_keys:
            raise errors.InputConfigError(
                f"Provided extra global inputs "
                f"not specified in configs: {extra_global_input_keys}"
            )

        return config

    def __eq__(self, other: Any) -> bool:
        return (
            type(other) is ConfigSpec
            and self.cls is other.cls
            and self.kwargs == other.kwargs
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.__class__.__name__,
                frozenset(self.kwargs.items()),
            )
        )


class Config:
    """dataclass-style description of params and obj graph."""

    _INTERNAL_FIELDS = (
        "_config_locator",
        "_keys",
        "_specs",
        "_child_configs",
        "_global_inputs",
        "_loaded",
        "_frozen",
        "_get_all_global_input_keys",
        "_process_input",
        "_load",
        "freeze",
    )

    def __new__(cls: Type, **kwargs):
        # noinspection PyTypeChecker
        return ConfigSpec(cls, **kwargs)

    def __init__(
        self, config_locator: Optional[ConfigLocator] = None, **local_inputs
    ):
        if config_locator is None:
            raise ValueError(
                "config_locator is only defaulted to "
                "None to aid PyCharm inspections. "
                "Use config's cls.get() instead."
            )
        self._config_locator = config_locator

        for value in local_inputs.values():
            if not isinstance(value, PRIMITIVE_TYPES):
                raise errors.InputConfigError(
                    f"Unsupported local input type: {type(value)}"
                )

        self._keys: Dict[specs.SpecID, str] = {}
        self._specs: Dict[str, specs.Spec] = {}
        self._child_configs: Dict[str, Config] = {}
        self._global_inputs: Dict[str, specs.SpecID] = {}

        self._loaded = False
        self._frozen = False

        self._load(**local_inputs)

    # For mypy
    def __call__(self, *args, **kwargs):
        return None

    def _get_all_global_input_keys(
        self, all_global_input_keys: Optional[Dict[str, specs.SpecID]] = None
    ) -> Set[str]:
        """Recursively get all global input keys of this config and all child
        configs."""
        all_global_input_keys = (
            all_global_input_keys if all_global_input_keys is not None else {}
        )

        for key, spec_id in self._global_inputs.items():
            if key in all_global_input_keys:
                if all_global_input_keys[key] != spec_id:
                    raise errors.InputConfigError(
                        f"Found global input collision: {key!r}"
                    )

            all_global_input_keys[key] = spec_id

        for key, child_config in self._child_configs.items():
            # noinspection PyProtectedMember
            child_config._get_all_global_input_keys(all_global_input_keys)

        return set(all_global_input_keys.keys())

    def _process_input(
        self, key: str, spec: specs.Input, inputs: Dict[str, Any], tag: str
    ) -> specs.Object:
        """Convert Input spec to Object spec."""
        try:
            value = inputs[key]
        except KeyError:
            if spec.default != specs.MISSING:
                value = spec.default
            else:
                raise errors.InputConfigError(f"{tag} input not set: {key!r}")

        check_type(value, spec.type_, tag=tag)

        new_spec = specs.Object(value)
        new_spec.spec_id = spec.spec_id
        return new_spec

    def _load(self, **local_inputs):
        """Transfer class variables to instance."""
        for key in self.__class__.__dict__:
            if (
                key.startswith("__")
                or key == "_INTERNAL_FIELDS"
                or key in self._INTERNAL_FIELDS
            ):
                continue

            spec = getattr(self.__class__, key)

            # Skip partial kwargs (no registration needed)
            if isinstance(spec, dict):
                continue

            if not isinstance(spec, specs.Spec):
                raise ValueError(
                    f"Expected Spec type, got {type(spec)} with {key!r}"
                )

            # Register key
            self._keys[spec.spec_id] = key

            # Handle inputs
            if isinstance(spec, specs.GlobalInput):
                self._global_inputs[key] = spec.spec_id

                spec = self._process_input(
                    key, spec, self._config_locator.global_inputs, "Global"
                )
            elif isinstance(spec, specs.LocalInput):
                spec = self._process_input(key, spec, local_inputs, "Local")

            # Handle child configs
            if isinstance(spec, ConfigSpec):
                child_config = self._config_locator.get(spec)
                self._child_configs[key] = child_config
            else:
                self._specs[key] = spec

        self._loaded = True

    def freeze(self):
        """Freeze to prevent any more perturbations to this Config instance."""
        self._frozen = True

    # NB: Have to override getattribute instead of getattr so as to
    # prevent initial, class-level values from being used.
    def __getattribute__(self, key: str) -> Union[specs.Spec, Config]:
        if (
            key.startswith("__")
            or key == "_INTERNAL_FIELDS"
            or key in self._INTERNAL_FIELDS
        ):
            return super().__getattribute__(key)

        try:
            if key in self._child_configs:
                return self._child_configs[key]
            else:
                return self._specs[key]
        except KeyError:
            raise KeyError(f"{self.__class__}: {key!r}")

    def __getitem__(self, key: str) -> Any:
        return utils.nested_getattr(self, key)

    def __setattr__(self, key: str, value: Any):
        if (
            key.startswith("__")
            or key == "_INTERNAL_FIELDS"
            or key in self._INTERNAL_FIELDS
        ):
            super().__setattr__(key, value)
            return

        if self._frozen:
            raise errors.FrozenConfigError(
                f"Cannot perturb frozen config: key={key!r}"
            )

        if key not in self._specs and self._loaded:
            if key in self._child_configs:
                raise errors.SetChildConfigError(
                    f"Cannot set child config: key={key!r}"
                )
            else:
                raise errors.NewKeyConfigError(
                    f"Cannot add new keys to a loaded config: key={key!r}"
                )

        old_spec = self._specs[key]

        if not isinstance(value, specs.Spec):
            value = specs.Object(value)

        self._specs[key] = value
        value.spec_id = old_spec.spec_id

    def __setitem__(self, key: str, value: Any):
        utils.nested_setattr(self, key, value)

    def __dir__(self) -> Iterable[str]:
        return sorted(
            list(self._specs.keys()) + list(self._child_configs.keys())
        )


class ConfigLocator:
    """Service locator to get instances of Configs by types."""

    def __init__(self, **global_inputs):
        self.global_inputs: Dict[str, Any] = global_inputs

        self._config_cache: Dict[ConfigSpec, Config] = {}

    def get(self, config_spec: ConfigSpec) -> Config:
        """Get Config instance by type."""
        try:
            return self._config_cache[config_spec]
        except KeyError:
            pass

        # noinspection PyProtectedMember
        config = config_spec._instantiate(self)
        self._config_cache[config_spec] = config
        return config

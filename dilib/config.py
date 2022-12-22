from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Set, Type, TypeVar, Union

import dilib.errors
import dilib.specs
import dilib.utils

T = TypeVar("T")
TC = TypeVar("TC", bound="Config")


class ConfigSpec(dilib.specs.Spec[TC]):
    """Represents nestable bag of types and values."""

    def __init__(self, cls: Type[TC], **local_inputs):
        super().__init__()
        self.cls = cls
        self.local_inputs = local_inputs

    def get(self, **global_inputs) -> Config:
        """Instantiate with given global inputs."""
        config_locator = ConfigLocator(**global_inputs)
        config = config_locator.get(self)

        # noinspection PyProtectedMember
        global_input_keys = config._get_all_global_input_keys()
        extra_global_input_keys = set(global_inputs.keys()) - global_input_keys
        if extra_global_input_keys:
            raise dilib.errors.InputConfigError(
                f"Provided extra global inputs "
                f"not specified in configs: {extra_global_input_keys}"
            )

        return config

    def __eq__(self, other: Any) -> bool:
        return (
            type(other) is ConfigSpec
            and self.cls is other.cls
            and self.local_inputs == other.local_inputs
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.__class__.__name__,
                frozenset(self.local_inputs.items()),
            )
        )


class Config:
    """Description of how specs depend on each other."""

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
        "_get_spec",
        "_get_child_class",
    )

    def __new__(cls: Type[TC], *args, _materialize: bool = False, **kwargs):
        if _materialize:
            return super().__new__(cls)
        else:
            if args:
                raise ValueError("args must be empty")

            return ConfigSpec(cls, **kwargs)

    def __init__(
        self, config_locator: Optional[ConfigLocator] = None, **local_inputs
    ):
        if config_locator is None:
            raise ValueError("Use config.get() to get instance of config")
        self._config_locator = config_locator

        # spec id -> spec key
        self._keys: Dict[dilib.specs.SpecID, str] = {}
        # key -> spec
        self._specs: Dict[str, dilib.specs.Spec] = {}
        # child config key -> child config
        self._child_configs: Dict[str, Config] = {}
        # global input key -> spec id
        self._global_inputs: Dict[str, dilib.specs.SpecID] = {}

        self._loaded = False
        self._frozen = False

        self._load(**local_inputs)

    # For mypy
    def __call__(self, *args, **kwargs) -> Any:
        return None

    def _get_all_global_input_keys(
        self,
        all_global_input_keys: Optional[Dict[str, dilib.specs.SpecID]] = None,
    ) -> Set[str]:
        """Recursively get all global input keys of self and its children."""
        all_global_input_keys = (
            all_global_input_keys if all_global_input_keys is not None else {}
        )

        for key, spec_id in self._global_inputs.items():
            if key in all_global_input_keys:
                if all_global_input_keys[key] != spec_id:
                    raise dilib.errors.InputConfigError(
                        f"Found global input collision: {key!r}"
                    )

            all_global_input_keys[key] = spec_id

        for key, child_config in self._child_configs.items():
            # noinspection PyProtectedMember
            child_config._get_all_global_input_keys(all_global_input_keys)

        return set(all_global_input_keys.keys())

    # noinspection PyProtectedMember
    def _process_input(
        self,
        key: str,
        spec: dilib.specs._Input,
        inputs: Dict[str, Any],
        desc: str,
    ) -> dilib.specs._Object:
        """Convert Input spec to Object spec."""
        try:
            value = inputs[key]
        except KeyError:
            if spec.default != dilib.specs.MISSING:
                value = spec.default
            else:
                raise dilib.errors.InputConfigError(
                    f"{desc} input not set: {key!r}"
                )

        dilib.utils.check_type(value, spec.type_, desc=desc)

        # Preserve old spec id
        return dilib.specs._Object(value, spec_id=spec.spec_id)

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

            if not isinstance(spec, dilib.specs.Spec):
                raise ValueError(
                    f"Expected Spec type, got {type(spec)} with {key!r}"
                )

            # Register key
            self._keys[spec.spec_id] = key

            # Handle inputs
            # noinspection PyProtectedMember
            if isinstance(spec, dilib.specs._GlobalInput):
                self._global_inputs[key] = spec.spec_id

                spec = self._process_input(
                    key, spec, self._config_locator.global_inputs, "Global"
                )
            # noinspection PyProtectedMember
            elif isinstance(spec, dilib.specs._LocalInput):
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

    def _get_spec(self, key: str) -> dilib.specs.Spec:
        """More type-safe alternative to get spec than attr access."""
        spec = self[key]
        if not isinstance(spec, dilib.specs.Spec):
            raise TypeError(type(spec))
        return spec

    def _get_child_config(self, key: str) -> Config:
        """More type-safe alternative to get child config than attr access."""
        child_config = self[key]
        if not isinstance(child_config, Config):
            raise TypeError(type(child_config))
        return child_config

    # NB: Have to override getattribute instead of getattr to
    # prevent initial, class-level values from being used.
    def __getattribute__(self, key: str) -> Union[dilib.specs.Spec, Config]:
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
        return dilib.utils.nested_getattr(self, key)

    def __contains__(self, key: str) -> Any:
        if "." in key:
            return dilib.utils.nested_contains(self, key)
        else:
            return key in dir(self)

    def __setattr__(self, key: str, value: Any):
        if (
            key.startswith("__")
            or key == "_INTERNAL_FIELDS"
            or key in self._INTERNAL_FIELDS
        ):
            super().__setattr__(key, value)
            return

        if self._frozen:
            raise dilib.errors.FrozenConfigError(
                f"Cannot perturb frozen config: key={key!r}"
            )

        if key not in self._specs and self._loaded:
            if key in self._child_configs:
                raise dilib.errors.SetChildConfigError(
                    f"Cannot set child config: key={key!r}"
                )
            else:
                raise dilib.errors.NewKeyConfigError(
                    f"Cannot add new keys to a loaded config: key={key!r}"
                )

        old_spec = self._specs[key]

        # Automatically wrap input if user hasn't done so
        if not isinstance(value, dilib.specs.Spec):
            value = dilib.specs.Object(value)

        self._specs[key] = value

        # Transfer old spec id
        value.spec_id = old_spec.spec_id

    def __setitem__(self, key: str, value: Any):
        dilib.utils.nested_setattr(self, key, value)

    def __dir__(self) -> Iterable[str]:
        return sorted(
            list(self._specs.keys()) + list(self._child_configs.keys())
        )


class ConfigLocator:
    """Service locator to get instances of Configs by type."""

    def __init__(self, **global_inputs):
        self.global_inputs: Dict[str, Any] = global_inputs

        self._config_cache: Dict[ConfigSpec, Config] = {}

    def get(self, config_spec: ConfigSpec) -> Config:
        """Get Config instance by type."""
        try:
            return self._config_cache[config_spec]
        except KeyError:
            pass

        config = dilib.specs.instantiate(
            config_spec.cls,
            self,
            _materialize=True,
            **config_spec.local_inputs,
        )
        self._config_cache[config_spec] = config
        return config


def get_config(config_cls: Type[TC], **global_inputs) -> TC:
    """More type-safe alternative to getting config objs."""
    return config_cls().get(**global_inputs)

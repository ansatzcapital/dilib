from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Union, cast

from dilib import di_config, specs, utils


class ConfigProxy:
    """Read-only helper to marshal config values."""

    def __init__(self, container: Container, config: di_config.Config):
        self.container = container
        self.config = config

    def __getattr__(self, key: str) -> Any:
        # noinspection PyProtectedMember
        return self.container._get(self.config, key)

    def __getitem__(self, key: str) -> Any:
        return utils.nested_getattr(self, key)

    def __dir__(self) -> Iterable[str]:
        return dir(self.config)


class Container:
    """Getter of (cached) instances."""

    def __init__(self, config: di_config.Config):
        if isinstance(config, di_config.ConfigSpec):
            raise ValueError(
                "Expected Config type, got ConfigSpec. "
                "Please call .get() on the config."
            )

        self._config = config
        self._config.freeze()

        self._instance_cache: Dict[Union[str, int], Any] = {}

    def _process_arg(self, config: di_config.Config, arg: Any) -> Any:
        if isinstance(arg, specs.Spec):
            # noinspection PyProtectedMember
            if arg.spec_id in config._keys:
                # noinspection PyProtectedMember
                config_key = config._keys[arg.spec_id]
                result = self._get(config, config_key)
            elif isinstance(arg, specs.Prototype):
                # Anonymous prototype or singleton
                result = self._materialize_spec(config, arg).instantiate()
            else:
                raise ValueError(f"Unrecognized arg type: {type(arg)}")
        elif isinstance(arg, specs.AttrFuture):
            # noinspection PyProtectedMember
            config_key = config._keys[arg.parent_spec_id]
            result = self._get(config, config_key)

            for attr in arg.attrs:
                result = getattr(result, attr)
        elif isinstance(arg, (tuple, list)):
            result = type(arg)(self._process_arg(config, elem) for elem in arg)
        elif isinstance(arg, dict):
            result = {k: self._process_arg(config, v) for k, v in arg.items()}
        else:
            result = arg

        return result

    def _materialize_spec(
        self, config: di_config.Config, spec: specs.Prototype
    ) -> specs.Prototype:
        """Return Spec copy with materialized args/kwargs."""
        materialized_args = [
            self._process_arg(config, arg) for arg in spec.args
        ]
        materialized_kwargs = {
            key: self._process_arg(config, arg)
            for key, arg in spec.kwargs.items()
        }
        if spec.lazy_kwargs:
            materialized_lazy_kwargs = self._process_arg(
                config, spec.lazy_kwargs
            )
            materialized_kwargs.update(
                {
                    key: self._process_arg(config, arg)
                    for key, arg in materialized_lazy_kwargs.items()
                }
            )

        return spec.copy_with(*materialized_args, **materialized_kwargs)

    def _get(self, config: di_config.Config, key: str) -> Any:
        """Get instance represented by key in given config."""
        spec = getattr(config, key)
        if isinstance(spec, specs.Object):
            return spec.obj
        elif isinstance(spec, specs.Singleton):
            try:
                return self._instance_cache[spec.spec_id]
            except KeyError:
                pass

            instance = self._materialize_spec(config, spec).instantiate()
            self._instance_cache[spec.spec_id] = instance
            return instance
        elif isinstance(spec, specs.Prototype):
            spec = cast(specs.Prototype, spec)
            return self._materialize_spec(config, spec).instantiate()
        elif isinstance(spec, di_config.Config):
            return ConfigProxy(self, spec)
        elif isinstance(spec, specs.AttrFuture):
            # noinspection PyProtectedMember
            key = config._keys[spec.parent_spec_id]
            obj = self._get(config, key)

            for idx, attr in enumerate(spec.attrs):
                obj = getattr(obj, attr)
                if idx == len(spec.attrs) - 1:
                    return obj

            raise ValueError(
                f"Failed to resolve attr reference: "
                f"spec_id={spec.spec_id}, attrs={spec.attrs}"
            )
        else:
            raise ValueError(f"Unrecognized spec type: {type(spec)}")

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        if key in dir(self):
            return self[key]

        return default

    def clear(self):
        """Clear instance cache."""
        self._instance_cache.clear()

    def __getattr__(self, key: str) -> Any:
        return self._get(self._config, key)

    def __getitem__(self, key: str) -> Any:
        return utils.nested_getattr(self, key)

    def __dir__(self) -> Iterable[str]:
        return dir(self._config)

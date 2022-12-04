from __future__ import annotations

from typing import Any, Dict, Generic, Iterable, Optional, TypeVar, Union, cast

from dilib import di_config, specs, utils

T = TypeVar("T", bound=di_config.ConfigProtocol)


class ConfigProxy(Generic[T]):
    """Read-only helper to marshal config values."""

    def __init__(self, container: Container[T], config: di_config.Config[T]):
        self.container = container
        self.config = config

    def __getattr__(self, key: str) -> Any:
        # noinspection PyProtectedMember
        return self.container._get(self.config, key)

    def __getitem__(self, key: str) -> Any:
        return utils.nested_getattr(self, key)

    def __dir__(self) -> Iterable[str]:
        return dir(self.config)


# noinspection PyProtectedMember
class Container(Generic[T]):
    """Getter of (cached) instances."""

    def __init__(self, config: di_config.Config[T]):
        if isinstance(config, di_config._ConfigSpec):
            raise ValueError(
                "Expected Config type, got _ConfigSpec. "
                "Please call dilib.get_config()."
            )

        self._config = config
        self._config.freeze()

        self._instance_cache: Dict[Union[str, int], Any] = {}

    @property
    def config(self) -> T:
        # Cast because ConfigProxy[T] will adhere to T config protocol
        return cast(T, ConfigProxy(self, self._config))

    def _process_arg(self, config: di_config.Config, arg: Any) -> Any:
        if isinstance(arg, specs.Spec):
            if arg.spec_id in config._keys:
                config_key = config._keys[arg.spec_id]
                result = self._get(config, config_key)
            elif isinstance(arg, specs._Prototype):
                # Anonymous prototype or singleton
                result = self._materialize_spec(config, arg).instantiate()
            else:
                raise ValueError(f"Unrecognized arg type: {type(arg)}")
        elif isinstance(arg, specs.AttrFuture):
            config_key = config._keys[arg.parent_spec_id]
            result = self._get(config, config_key)

            for attr in arg.attrs:
                result = getattr(result, attr)
        else:
            result = arg

        return result

    def _materialize_spec(
        self, config: di_config.Config, spec: specs._Prototype
    ) -> specs._Prototype:
        """Return Spec copy with materialized args/kwargs."""
        materialized_args = [
            self._process_arg(config, arg) for arg in spec.args
        ]
        materialized_kwargs = {
            key: self._process_arg(config, arg)
            for key, arg in spec.kwargs.items()
        }

        return spec.copy_with(*materialized_args, **materialized_kwargs)

    def _get(self, config: di_config.Config, key: str) -> Any:
        """Get instance represented by key in given config."""
        spec = getattr(config, key)
        if isinstance(spec, specs._Object):
            return spec.obj
        elif isinstance(spec, specs._Singleton):
            try:
                return self._instance_cache[spec.spec_id]
            except KeyError:
                pass

            instance = self._materialize_spec(config, spec).instantiate()
            self._instance_cache[spec.spec_id] = instance
            return instance
        elif isinstance(spec, specs._Prototype):
            spec = cast(specs._Prototype, spec)
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

    def __getitem__(self, key: str) -> Any:
        return utils.nested_getattr(self.config, key)


def get_container(config: di_config.Config[T]) -> Container[T]:
    return Container(config)

from typing import Any


def nested_getattr(obj: Any, key: str) -> Any:
    for key_part in key.split("."):
        obj = getattr(obj, key_part)
    return obj


def nested_setattr(obj: Any, key: str, value: Any):
    split_key = key.split(".")
    for index, key_part in enumerate(split_key):
        if index < len(split_key) - 1:
            obj = getattr(obj, key_part)
        else:
            setattr(obj, key_part, value)

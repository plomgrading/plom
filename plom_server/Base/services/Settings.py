# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from typing import Any

from ..models import NewSettingsModel


def key_value_store_get(key: str, default: bool | Any | None = None) -> Any:
    """Lookup a key to get a value from the key-value store.

    If the key does not exist, return ``None`` (can be customized with
    a kwarg).

    Args:
        key: a unique string key.

    Keyword Args:
        default: if they key does not exist, return this value,
            which is ``None`` if omitted.

    Returns:
        The value associated with that key.
    """
    try:
        return NewSettingsModel.objects.get(key=key).value
    except NewSettingsModel.DoesNotExist:
        return default


def key_value_store_set(key: str, value: Any) -> None:
    """Store something in the key-value store.

    Args:
        key: a unique string key.
        value: something that can be serialized and stored
            to JSON.
    """
    obj, created = NewSettingsModel.objects.get_or_create(key=key)
    obj.value = value
    obj.save()

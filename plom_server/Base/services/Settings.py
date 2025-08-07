# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from copy import deepcopy
from typing import Any

from plom.feedback_rules import feedback_rules as static_feedback_rules
from ..models import SettingsModel


# If no value is set in the database, we use defaults recorded here
default_settings = {
    "who_can_create_rubrics": "permissive",
    "who_can_modify_rubrics": "per-user",
    "feedback_rules": deepcopy(static_feedback_rules),
    "prenaming_enabled": False,
    "prenaming_xcoord": 50,
    "prenaming_ycoord": 42,
}


def key_value_store_get(key: str) -> Any:
    """Lookup a key to get a value from the key-value store.

    If the key does not exist *in the database*, return the (per-key)
    default value.  But if no default value exists, raise a KeyError.

    Args:
        key: a unique string key.

    Returns:
        The value associated with that key.

    Raises:
        KeyError: querying an unknown key, that also doesn't have a
            default value.
    """
    try:
        return SettingsModel.objects.get(key=key).value
    except SettingsModel.DoesNotExist:
        return default_settings[key]


def key_value_store_set(key: str, value: Any) -> None:
    """Store something in the key-value store.

    Args:
        key: a unique string key.
        value: something that can be serialized and stored
            to JSON.
    """
    obj, created = SettingsModel.objects.get_or_create(key=key)
    obj.value = value
    obj.save()


def key_value_store_reset(key: str) -> None:
    """Reset something in the key-value store to its default value.

    Args:
        key: a unique string key.
    """
    obj, created = SettingsModel.objects.get_or_create(key=key)
    obj.value = default_settings[key]
    obj.save()


def get_feedback_rules():
    """Get a copy of the current value of the feedback rules."""
    return key_value_store_get("feedback_rules")


def get_who_can_create_rubrics() -> str:
    """Get the level of restrictions on who can create rubrics, or a default if not set."""
    return key_value_store_get("who_can_create_rubrics")


def set_who_can_create_rubrics(x: str) -> None:
    """Set the restriction for who can create rubrics to one of "permissive", "per-user" or "locked."""
    choices = ("permissive", "per-user", "locked")
    if x not in choices:
        raise ValueError(f'"{x}" is invalid, must be one of {choices}')
    key_value_store_set("who_can_create_rubrics", x)


def get_who_can_modify_rubrics() -> str:
    """Get the level of restrictions on who can modify rubrics, or a default if not set."""
    return key_value_store_get("who_can_modify_rubrics")


def set_who_can_modify_rubrics(x: str) -> None:
    """Set the restriction for who can modify rubrics to one of "permissive", "per-user" or "locked."""
    choices = ("permissive", "per-user", "locked")
    if x not in choices:
        raise ValueError(f'"{x}" is invalid, must be one of {choices}')
    key_value_store_set("who_can_modify_rubrics", x)

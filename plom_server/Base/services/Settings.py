# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Colin B. Macdonald

from copy import deepcopy
from typing import Any

from django.conf import settings

from plom.tpv_utils import new_magic_code, is_valid_public_code
from plom.feedback_rules import feedback_rules as static_feedback_rules
from ..models import SettingsModel


# If no value is set in the database, we use defaults recorded here
default_settings = {
    "task_order_strategy": "paper_number",
    "have_papers_been_printed": False,
    "who_can_create_rubrics": "permissive",
    "who_can_modify_rubrics": "per-user",
    "feedback_rules": deepcopy(static_feedback_rules),
    "prenaming_xcoord": 50,
    "prenaming_ycoord": 42,
    # I recall being unhappy about this setting and its potential for abuse,
    # so give it a underscore name: IIRC, it is a very transcient notion of
    # how many papers to produce, and should not be widely trusted/consulted
    "_tmp_number_of_papers_to_produce": 0,
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


def key_value_store_get_or_none(key: str) -> Any:
    """Lookup a key to get a value from the key-value store.

    If the key does not exist *in the database*, and has no default
    value, return None.

    Args:
        key: a unique string key.

    Returns:
        The value associated with that key or None.
    """
    try:
        return key_value_store_get(key)
    except KeyError:
        return None


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


def get_public_code() -> str | None:
    """Return the public code or None if there isn't one."""
    return key_value_store_get_or_none("public_code")


def set_public_code(public_code: str) -> None:
    """Change the public code."""
    if not is_valid_public_code(public_code):
        raise ValueError("invalid public code")
    key_value_store_set("public_code", public_code)


def get_or_create_new_public_code():
    """Carefully return the current public code or create a new one.

    If two people call almost simultaneously, they should get the same code.
    """
    obj, _created = SettingsModel.objects.get_or_create(
        key="public_code", defaults={"value": new_magic_code()}
    )
    return obj.value


def create_new_random_public_code():
    """Create a new random public code, independent of whether one already exists."""
    set_public_code(new_magic_code())


def get_paper_size_in_pts() -> tuple[int, int]:
    """Return the current paper size as a pair, in units of points."""
    import pymupdf

    return pymupdf.paper_size(settings.PAPERSIZE)


def get_paper_size() -> str:
    """Return a one-word code for the current papersize, such as "letter" or "A4".

    Note the case is not converted: if you set (in the env var) "A4" then
    this function will return "A4".
    """
    return settings.PAPERSIZE


def get_paper_size_for_latex() -> str:
    """Return a one-word code for the current papersize, appropriate for LaTeX, such as "a4paper".

    Note LaTeX expects lowercase: "a4paper" not "A4paper"; we do that conversion.
    """
    return (settings.PAPERSIZE + "paper").lower()

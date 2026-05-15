# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from typing import Any

from plom_server import __version__ as plom_version
from plom_server.Authentication.services import AuthService
from plom_server.Papers.services import SpecificationService


def user_group_information(request) -> dict[str, Any]:
    """Add user group membership booleans to every view context.

    Adds booleans "user_is_<X>" for the various groups.
    """
    this_user_groups = list(request.user.groups.values_list("name", flat=True))
    context = {
        f"user_is_{g}": g in this_user_groups for g in AuthService.plom_user_groups_list
    }
    return context


def plom_information(request):
    """Adds Plom version and assessment information to every view context."""
    shortname, longname = SpecificationService.get_short_and_long_names_or_empty()
    return {
        "plom_version": plom_version,
        "assessment_shortname_if_defined": shortname,
        "assessment_longname_if_defined": longname,
    }

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from plom_server import __version__ as plom_version
from plom_server.Papers.services import SpecificationService


def user_group_information(request):
    """Add user group membership booleans to every view context.

    Adds booleans "user_is_<X>" for the various groups.
    """
    group_list = list(request.user.groups.values_list("name", flat=True))
    context = {
        "user_is_admin": "admin" in group_list,
        "user_is_manager": "manager" in group_list,
        "user_is_scanner": "scanner" in group_list,
        "user_is_lead_marker": "lead_marker" in group_list,
        "user_is_marker": "marker" in group_list,
        "user_is_identifier": "identifier" in group_list,
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

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer


def user_group_information(request):
    # Use following colors for nav bar for groups {
    #     "admin": "danger",
    #     "manager": "warning",
    #     "scanner": "info",
    #     "marker": "primary",   # use marker as the default color
    #     "lead_marker": "dark",
    # }
    group_list = list(request.user.groups.values_list("name", flat=True))
    context = {
        "user_is_admin": "admin" in group_list,
        "user_is_manager": "manager" in group_list,
        "user_is_scanner": "scanner" in group_list,
        "user_is_lead_marker": "lead_marker" in group_list,
        "user_is_marker": "marker" in group_list,
        "navbar_colour": "primary",  # default to the marker color, no 'u' to keep north americans happy
    }
    if "admin" in group_list:
        context["navbar_color"] = "danger"
    elif "manager" in group_list:
        context["navbar_color"] = "warning"
    elif "scanner" in group_list:
        context["navbar_color"] = "info"
    elif "lead_marker" in group_list:
        context["navbar_color"] = "dark"
    return context

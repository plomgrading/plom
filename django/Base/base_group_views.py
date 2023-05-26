# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.views.generic import View
from braces.views import LoginRequiredMixin, GroupRequiredMixin


# Create your views here.
class AdminRequiredView(LoginRequiredMixin, GroupRequiredMixin, View):
    """A base class view for admins."""

    group_required = ["admin"]
    login_url = "login"
    navbar_colour = "#808080"
    raise_exception = True

    def build_context(self):
        context = {
            "navbar_colour": self.navbar_colour,
            "user_group": self.group_required[0],
        }

        return context


class ManagerRequiredView(LoginRequiredMixin, GroupRequiredMixin, View):
    """A base class view for managers."""

    group_required = ["manager"]
    login_url = "login"
    navbar_colour = "#AD9CFF"
    raise_exception = True

    def build_context(self):
        context = {
            "navbar_colour": self.navbar_colour,
            "user_group": self.group_required[0],
        }

        return context


class ScannerRequiredView(LoginRequiredMixin, GroupRequiredMixin, View):
    """A base class view for scanners."""

    group_required = ["scanner"]
    login_url = "login"
    navbar_colour = "#0F984F"
    raise_exception = True
    redirect_unauthenticated_users = True

    def build_context(self):
        context = {
            "navbar_colour": self.navbar_colour,
            "user_group": self.group_required[0],
        }

        return context


class MarkerRequiredView(LoginRequiredMixin, GroupRequiredMixin, View):
    """A base class view for markers."""

    group_required = ["marker"]
    login_url = "login"
    navbar_colour = "#0F984F"
    raise_exception = True

    def build_context(self):
        context = {
            "navbar_colour": self.navbar_colour,
            "user_group": self.group_required[0],
        }

        return context

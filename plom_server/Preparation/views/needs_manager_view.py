# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from braces.views import GroupRequiredMixin, LoginRequiredMixin
from django.views import View


class ManagerRequiredBaseView(LoginRequiredMixin, GroupRequiredMixin, View):
    login_url = "login"
    group_required = ["manager"]

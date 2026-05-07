# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2026 Aidan Murphy

from braces.views import GroupRequiredMixin, LoginRequiredMixin
from django.views import View


class ManagerRequiredBaseView(LoginRequiredMixin, GroupRequiredMixin, View):
    group_required = ["manager"]

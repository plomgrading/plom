# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView


class ProgressMarkHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()
        return render(request, "Progress/Mark/mark_home.html", context)

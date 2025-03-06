# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

from django.shortcuts import render

from plom_server.Base.base_group_views import ManagerRequiredView


class MiscExtrasView(ManagerRequiredView):
    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/misc_extras.html", context)

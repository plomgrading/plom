# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView


class SolnHomeView(ManagerRequiredView):
    def get(self, request):
        context = self.build_context()
        return render(request, "Finish/soln_home.html", context=context)

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from Papers.services import SolnSpecService


class SolnHomeView(ManagerRequiredView):
    def get(self, request):
        context = self.build_context()
        context.update({"is_there_a_soln_spec": SolnSpecService.is_there_a_soln_spec()})
        return render(request, "Finish/soln_home.html", context=context)

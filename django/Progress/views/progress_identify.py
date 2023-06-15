# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from Identify.services import IdentifyTaskService
from Papers.models import IDPage


class ProgressIdentifyHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()

        # id_progress = IdentifyTaskService().get_id_progress()
        # print(id_progress)
        paper_amount = []
        for i in range(1, 51):
            paper_amount.append(i)
        
        context.update({
            "paper_amount": paper_amount,
        })
        return render(request, "Progress/Identify/identify_home.html", context)
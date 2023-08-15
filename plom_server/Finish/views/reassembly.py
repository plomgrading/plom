# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import csv
from io import StringIO

import arrow

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from ..services import ReassembleService


class ReassemblePapersView(ManagerRequiredView):
    def get(self, request):
        reas = ReassembleService()
        context = self.build_context()
        context.update({"papers": reas.alt_get_all_paper_status()})
        return render(request, "Finish/reassemble_paper_pdfs.html", context=context)

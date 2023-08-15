# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ManagerRequiredView
from ..services import ReassembleService


class ReassemblePapersView(ManagerRequiredView):
    def get(self, request):
        reas = ReassembleService()
        context = self.build_context()
        context.update({"papers": reas.alt_get_all_paper_status()})
        return render(request, "Finish/reassemble_paper_pdfs.html", context=context)


class StartOneReassembly(ManagerRequiredView):
    def post(self, request, paper_number):
        ReassembleService().queue_single_paper_reassembly(paper_number)
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))

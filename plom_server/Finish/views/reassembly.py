# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import render
from django.http import HttpResponseRedirect, FileResponse
from django.urls import reverse
from django_htmx.http import HttpResponseClientRedirect

from Base.base_group_views import ManagerRequiredView
from ..services import ReassembleService


class ReassemblePapersView(ManagerRequiredView):
    def get(self, request):
        reas = ReassembleService()
        context = self.build_context()
        all_paper_status = reas.alt_get_all_paper_status()
        # compute some numbers
        n_papers = sum([1 for n, x in all_paper_status.items() if x["scanned"]])
        n_not_ready = sum(
            [
                1
                for n, x in all_paper_status.items()
                if x["scanned"] and not (x["identified"] and x["marked"])
            ]
        )
        n_ready = sum(
            [1 for n, x in all_paper_status.items() if x["identified"] and x["marked"]]
        )
        n_outdated = sum([1 for n, x in all_paper_status.items() if x["outdated"]])
        n_queued = sum(
            [
                1
                for n, x in all_paper_status.items()
                if x["reassembled_status"] == "Queued"
            ]
        )
        n_errors = sum(
            [
                1
                for n, x in all_paper_status.items()
                if x["reassembled_status"] == "Error"
            ]
        )
        n_complete = sum(
            [
                1
                for n, x in all_paper_status.items()
                if x["reassembled_status"] == "Complete"
            ]
        )

        context.update(
            {
                "papers": all_paper_status,
                "n_papers": n_papers,
                "n_not_ready": n_not_ready,
                "n_ready": n_ready,
                "n_outdated": n_outdated,
                "n_errors": n_errors,
                "n_complete": n_complete,
                "n_queued": n_queued,
            }
        )
        return render(request, "Finish/reassemble_paper_pdfs.html", context=context)


class StartOneReassembly(ManagerRequiredView):
    def post(self, request, paper_number):
        ReassembleService().queue_single_paper_reassembly(paper_number)
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))

    def delete(self, request, paper_number):
        ReassembleService().reset_single_paper_reassembly(paper_number)
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))

    def get(self, request, paper_number):
        pdf_file = ReassembleService().get_single_reassembled_file(paper_number)
        return FileResponse(pdf_file)

    def put(self, request, paper_number):  # called by "re-reassemble"
        ReassembleService().reset_single_paper_reassembly(paper_number)
        ReassembleService().queue_single_paper_reassembly(paper_number)
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))


class StartAllReassembly(ManagerRequiredView):
    def post(self, request):
        ReassembleService().queue_all_paper_reassembly()
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))

    def delete(self, request):
        ReassembleService().reset_all_paper_reassembly()
        return HttpResponseClientRedirect(reverse("reassemble_pdfs"))

    # def get(self, request, paper_number):
    # pdf_file = ReassembleService().get_single_reassembled_file(paper_number)
    # return FileResponse(pdf_file)

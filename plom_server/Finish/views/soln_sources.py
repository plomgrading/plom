# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist

from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponseRedirect, FileResponse, Http404

from django_htmx.http import HttpResponseClientRedirect


from plom_server.Base.base_group_views import ManagerRequiredView

from ..services import SolnSourceService, BuildSolutionService
from plom_server.Papers.services import SolnSpecService, SpecificationService


class SolnSourcesView(ManagerRequiredView):
    def get(self, request, version=None):
        context = self.build_context()
        if not SolnSpecService.is_there_a_soln_spec():
            return HttpResponseRedirect(reverse("soln_home"))

        # version is non-null when user wants to download the source.
        if version:
            try:
                source_bytes = SolnSourceService().get_soln_pdf_for_download(version)
                return FileResponse(
                    source_bytes,
                    as_attachment=True,
                    filename=f"solution{version}.pdf",
                )
            except ObjectDoesNotExist:
                raise Http404("No such file")

        solns = SolnSourceService.get_list_of_sources()
        hashes = [s["hash"] for s in solns if s["uploaded"]]
        if len(hashes) != len(set(hashes)):
            dupes_warning = True
        else:
            dupes_warning = False

        context.update(
            {
                "versions": SpecificationService.get_n_versions(),
                "number_of_soln_pdfs": SolnSourceService().get_number_of_solution_pdf(),
                "soln_sources": solns,
                "dupes_warning": dupes_warning,
            }
        )
        return render(request, "Finish/soln_sources.html", context)

    def delete(self, request, version=None):
        # reset any built soln pdfs as well as delete this soln source pdf.
        if version:
            BuildSolutionService().reset_all_soln_build()
            SolnSourceService.remove_solution_pdf(version)

        return HttpResponseClientRedirect(reverse("soln_sources"))

    def post(self, request, version=None):
        if not version or not request.FILES["soln_pdf"]:
            HttpResponseRedirect(reverse("soln_sources"))

        context = self.build_context()
        try:
            SolnSourceService().take_solution_source_pdf_from_upload(
                version, request.FILES["soln_pdf"]
            )
            context["success"] = True
        except ValueError as err:
            context["success"] = False
            context["message"] = f"{err}"
        return render(request, "Finish/soln_source_attempt.html", context)

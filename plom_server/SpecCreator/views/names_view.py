# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse

from Preparation.services import TestSourceService, PQVMappingService

from . import TestSpecPageView
from ..services import StagingSpecificationService
from .. import forms


class TestSpecCreatorNamesPage(TestSpecPageView):
    """Set the test's long name, short name, and number of versions."""

    def build_form(self):
        spec = StagingSpecificationService()
        initial = {
            "long_name": spec.get_long_name(),
            "short_name": spec.get_short_name(),
        }

        versions = spec.get_n_versions()
        if versions:
            initial.update({"versions": versions})

        form = forms.TestSpecNamesForm(initial=initial)
        return form

    def build_context(self):
        context = super().build_context("names")
        context.update({"form": self.build_form()})
        return context

    def get(self, request):
        context = self.build_context()
        context.update({"form": self.build_form()})
        return render(request, "SpecCreator/names-page.html", context)

    def post(self, request):
        context = self.build_context()
        form = forms.TestSpecNamesForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            spec = StagingSpecificationService()

            long_name = data["long_name"]
            spec.set_long_name(long_name)

            short_name = data["short_name"]
            spec.set_short_name(short_name)

            n_versions = data["versions"]

            # if the number of versions has changed, and there are
            # test sources or a QV map uploaded, delete them
            if n_versions != spec.get_n_versions():
                tss = TestSourceService()
                tss.delete_all_test_sources()
                pqv = PQVMappingService()
                pqv.remove_pqv_map()

            spec.set_n_versions(n_versions)
            if n_versions == 1:
                spec.fix_all_questions()

            return HttpResponseRedirect(reverse("upload"))
        else:
            context.update({"form": form})
            return render(request, "SpecCreator/names-page.html", context)

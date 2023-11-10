# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.urls import reverse

from Base.base_group_views import ManagerRequiredView
from Papers.services import PaperInfoService, SpecificationService


class TestSpecPageView(ManagerRequiredView):
    def dispatch(self, request, *args, **kwargs):
        """Redirect to the assessment preparation page if the Papers database is already populated."""
        paper_info = PaperInfoService()
        if paper_info.is_paper_database_populated():
            return HttpResponseRedirect(reverse("prep_landing"))
        return super().dispatch(request, *args, **kwargs)

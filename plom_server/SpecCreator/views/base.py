# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald

from django.http import HttpResponseRedirect
from django.urls import reverse

from Base.base_group_views import ManagerRequiredView
from Papers.services import PaperInfoService


class SpecBaseView(ManagerRequiredView):
    def dispatch(self, request, *args, **kwargs):
        """Redirect to the assessment preparation page if the Papers database is already populated."""
        if PaperInfoService.is_paper_database_populated():
            return HttpResponseRedirect(reverse("prep_landing"))
        return super().dispatch(request, *args, **kwargs)

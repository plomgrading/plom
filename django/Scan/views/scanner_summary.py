# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

from django.http import HttpResponse
from Base.base_group_views import ScannerRequiredView


class ScannerSummaryView(ScannerRequiredView):
    """
    Display the summary of the whole test
    """

    def get(self, request):

        return HttpResponse("I am Summary initial page")

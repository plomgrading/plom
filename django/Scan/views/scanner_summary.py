# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.http import HttpResponse
from Base.base_group_views import ScannerRequiredView
from Scan.services import ScanService


class ScannerSummaryView(ScannerRequiredView):
    """
    Display the summary of the whole test
    """

    def get(self, request):
        scanner = ScanService()
        img = scanner.get_image(1673999616.639863, request.user, 10)
        
        print(img)
        return HttpResponse("I am Summary initial page")

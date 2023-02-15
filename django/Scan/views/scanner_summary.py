# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu

from django.http import HttpResponse
from Base.base_group_views import ScannerRequiredView
from Scan.services import ScanService
from Scan.models import StagingImage


class ScannerSummaryView(ScannerRequiredView):
    """
    Display the summary of the whole test
    """

    def get(self, request):
        scanner = ScanService()
        all_obj = StagingImage.objects.all()
        print(all_obj[27:])
        for i in all_obj[27:]:
            print("before", i.bundle_order)
            print(i.bundle_order - 1)
            print(i.file_path)

        return HttpResponse("I am Summary initial page")

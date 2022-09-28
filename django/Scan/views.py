# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.http import HttpResponse

from Base.base_group_views import ScannerRequiredView


class ScannerHomeView(ScannerRequiredView):
    """
    Hello, world!
    """

    def get(self, request):
        return HttpResponse("Scan")

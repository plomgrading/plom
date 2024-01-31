# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from django.shortcuts import render

from Base.base_group_views import ScannerRequiredView


class TroublesAfootGenericErrorView(ScannerRequiredView):
    def get(self, request):
        context = self.build_context()
        return render(request, "Scan/troubles_afoot.html", context)

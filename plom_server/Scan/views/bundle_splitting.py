# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

from django.shortcuts import render
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView

from ..services import ScanService


class BundleSplittingProgressView(ScannerRequiredView):
    """Display a spinner and progress bar during background rendering."""

    def get(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        context.update({"timestamp": timestamp})

        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        if not bundle:
            raise Http404()

        # if the splitting is already complete, redirect to the manage view
        n_completed = scanner.get_n_completed_page_rendering_tasks(bundle)
        n_total = scanner.get_n_page_rendering_tasks(bundle)
        if n_completed == n_total:
            scanner.page_splitting_cleanup(bundle)
            return HttpResponseRedirect(
                reverse("scan_manage_bundle", args=(timestamp, 0))
            )

        return render(request, "Scan/to_image_progress.html", context)


class BundleSplittingUpdateView(ScannerRequiredView):
    """Return an updated progress card to be displayed on the bundle splitting progress view."""

    def get(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        n_completed = scanner.get_n_completed_page_rendering_tasks(bundle)
        n_total = scanner.get_n_page_rendering_tasks(bundle)

        if n_completed == n_total:
            return HttpResponseClientRefresh()

        context.update(
            {
                "n_completed": n_completed,
                "n_total": n_total,
                "progress_percent": f"{int(n_completed / n_total * 100)}%",
                "timestamp": timestamp,
            }
        )

        return render(request, "Scan/fragments/to_image_card.html", context)

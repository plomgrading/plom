# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer

from django.shortcuts import render
from django.http import FileResponse
from django_htmx.http import HttpResponseClientRefresh

from plom_server.Base.base_group_views import LeadMarkerOrManagerView

from plom_server.Identify.services import IDProgressService
from ..services import ProgressOverviewService


class ProgressIdentifyHome(LeadMarkerOrManagerView):
    def get(self, request):
        context = super().build_context()

        ids = IDProgressService()

        id_task_status_counts = ProgressOverviewService().get_id_task_status_counts()
        n_all_id_task = sum(id_task_status_counts.values())
        context.update(
            {
                "id_task_info": ids.get_all_id_task_info(),
                "all_task_count": n_all_id_task,
                "id_task_status_counts": id_task_status_counts,
            }
        )

        return render(request, "Progress/Identify/identify_home.html", context)


class IDImageWrapView(LeadMarkerOrManagerView):
    def get(self, request, image_pk):
        id_img = IDProgressService().get_id_image_object(image_pk=image_pk)
        # pass -angle to template since css uses clockwise not anti-clockwise.
        context = {"image_pk": image_pk, "angle": -id_img.rotation}
        return render(request, "Progress/Identify/id_image_wrap_fragment.html", context)


class IDImageView(LeadMarkerOrManagerView):
    def get(self, request, image_pk):
        id_img = IDProgressService().get_id_image_object(image_pk=image_pk)
        return FileResponse(id_img.image_file)


class ClearID(LeadMarkerOrManagerView):
    def delete(self, request, paper_number):
        IDProgressService().clear_id_from_paper(paper_number)
        return HttpResponseClientRefresh()

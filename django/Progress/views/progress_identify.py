# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.shortcuts import render
from django.http import FileResponse

from Base.base_group_views import ManagerRequiredView

from Identify.services import IDService
from Papers.models import Image


class ProgressIdentifyHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()

        ids = IDService()
        all_id_papers = ids.get_all_id_papers()
        identified_papers = ids.get_identified_papers()
        unidentified_papers = ids.get_all_unidentified_papers()

        context.update(
            {
                "all_id_papers": all_id_papers,
                "all_id_papers_count": all_id_papers.count(),
                "identified_papers_count": identified_papers.count(),
                "unidentified_papers_count": unidentified_papers.count(),
            }
        )
        return render(request, "Progress/Identify/identify_home.html", context)


class IDImageView(ManagerRequiredView):
    def get(self, request, img_pk):
        id_img = IDService().get_id_image_object(img_pk=img_pk)
        return FileResponse(id_img.image_file)

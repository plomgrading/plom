# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer

from django.shortcuts import render
from django.http import FileResponse, HttpResponse
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ManagerRequiredView, LeadMarkerOrManagerView

from Progress.services import ManageScanService, ManageDiscardService
from Scan.services import hard_rotate_image_from_file_by_exif_and_angle


class ScanCompleteView(ManagerRequiredView):
    """View the table of complete pushed papers."""

    def get(self, request):
        mss = ManageScanService()

        # this is a dict - key is paper_number, value = list of pages
        completed_papers_dict = mss.get_all_completed_test_papers()
        # turn into list of tuples (key, value) ordered by key
        completed_papers_list = [
            (pn, pgs) for pn, pgs in sorted(completed_papers_dict.items())
        ]

        context = self.build_context()
        context.update(
            {
                "current_page": "complete",
                "number_of_completed_papers": len(completed_papers_dict),
                "completed_papers_list": completed_papers_list,
            }
        )
        return render(request, "Progress/scan_complete.html", context)


class PushedImageView(LeadMarkerOrManagerView):
    """Return a pushed image given by its pk."""

    def get(self, request, img_pk):
        img_obj = ManageScanService().get_pushed_image(img_pk)
        return FileResponse(img_obj.image_file)

    def delete(self, request, img_pk):
        mds = ManageDiscardService()
        mds.discard_pushed_image_from_pk(request.user, img_pk)
        return HttpResponseClientRefresh()


class PushedImageRotatedView(LeadMarkerOrManagerView):
    """Return a pushed image given by its pk, pass back hard rotated image."""

    def get(self, request, img_pk):
        img_obj = ManageScanService().get_pushed_image(img_pk)

        return HttpResponse(
            hard_rotate_image_from_file_by_exif_and_angle(
                img_obj.image_file, theta=img_obj.rotation
            ),
            content_type="image/png",
        )


class PushedImageWrapView(LeadMarkerOrManagerView):
    """Return the simple html wrapper around the pushed image with correct rotation."""

    def get(self, request, img_pk):
        mss = ManageScanService()
        pushed_img = mss.get_pushed_image(img_pk)
        pushed_img_page_info = mss.get_pushed_image_page_info(img_pk)

        # pass negative of angle for css rotation since it uses positive=clockwise (sigh)
        context = {
            "image_pk": img_pk,
            "angle": -pushed_img.rotation,
            "page_info": pushed_img_page_info,
        }

        return render(request, "Progress/fragments/pushed_image_wrapper.html", context)

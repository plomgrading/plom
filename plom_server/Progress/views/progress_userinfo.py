# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from ..services import UserInfoServices


class ProgressUserInfoHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()
        uis = UserInfoServices()

        annotations_exist = uis.annotation_exists()
        annotation_count_dict = uis.get_total_annotations_based_on_user()
        annotations_grouped_by_user = uis.get_annotations_based_on_user()
        annotations_grouped_by_question_num_ver = (
            uis.get_annotations_based_on_question_number_version(
                annotations_grouped_by_user
            )
        )

        context.update(
            {
                "annotations_exist": annotations_exist,
                "annotation_count_dict": annotation_count_dict,
                "annotations_grouped_by_user": annotations_grouped_by_user,
            }
        )
        return render(request, "Progress/User_Info/user_info_home.html", context)

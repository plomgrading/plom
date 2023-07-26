# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from Progress.services import UserInfoServices


class ProgressUserInfoHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()
        uis = UserInfoServices()

        annotations_exist = uis.annotation_exists()
        annotation_data_dict = uis.get_total_annotations_based_on_user()
        grouped_annotations = (
            uis.get_annotations_based_on_user_and_question_number_version()
        )

        context.update(
            {
                "annotations_exist": annotations_exist,
                "annotation_data_dict": annotation_data_dict,
                "grouped_annotations": grouped_annotations,
            }
        )
        return render(request, "Progress/User_Info/user_info_home.html", context)

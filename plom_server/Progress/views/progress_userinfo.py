# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from ..forms import AnnotationFilterForm
from ..services import UserInfoServices


class ProgressUserInfoHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()
        uis = UserInfoServices()
        filter_form = AnnotationFilterForm(request.GET)

        annotations_exist = uis.annotation_exists()
        annotation_count_dict = uis.get_total_annotations_count_based_on_user()
        latest_updated_annotation = uis.get_latest_updated_annotation()
        print(type(latest_updated_annotation))

        if filter_form.is_valid():
            day_filter = filter_form.cleaned_data["day_filter"]
            hour_filter = filter_form.cleaned_data["hour_filter"]
            minute_filter = filter_form.cleaned_data["minute_filter"]

            if not day_filter:
                day_filter = 0

            if not hour_filter:
                hour_filter = 0

            if not minute_filter:
                minute_filter = 0

            filtered_annotations = uis.filter_annotations_by_time(
                days=int(day_filter), hours=int(hour_filter), minutes=int(minute_filter)
            )

        annotations_grouped_by_user = uis.get_annotations_based_on_user(
            filtered_annotations
        )
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
                "annotations_grouped_by_question_num_ver": annotations_grouped_by_question_num_ver,
                "annotation_filter_form": filter_form,
                "latest_updated_annotation": latest_updated_annotation,
            }
        )
        return render(request, "Progress/User_Info/user_info_home.html", context)

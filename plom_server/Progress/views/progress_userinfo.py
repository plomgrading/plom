# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Elisa Pan

from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from ..forms import AnnotationFilterForm
from ..services import UserInfoServices

from django.contrib.auth.models import User
from UserManagement.models import ProbationPeriod


class ProgressUserInfoHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()
        uis = UserInfoServices()
        filter_form = AnnotationFilterForm(request.GET)

        annotations_exist = uis.annotation_exists()
        annotated_and_claimed_count_dict = (
            uis.get_total_annotated_and_claimed_count_based_on_user()
        )
        latest_annotation_human_time = uis.get_time_of_latest_updated_annotation()
        request_time_filter_seconds = request.GET.get("time_filter_seconds")

        if filter_form.is_valid():
            time_filter_seconds = filter_form.cleaned_data["time_filter_seconds"]
            if not time_filter_seconds:
                time_filter_seconds = 0
            filtered_annotations = uis.filter_annotations_by_time_delta_seconds(
                time_delta_seconds=int(time_filter_seconds)
            )
        # not one of the available choices then
        else:
            if request_time_filter_seconds.isnumeric():
                filtered_annotations = uis.filter_annotations_by_time_delta_seconds(
                    time_delta_seconds=int(request_time_filter_seconds)
                )
            else:
                filtered_annotations = uis.filter_annotations_by_time_delta_seconds(
                    time_delta_seconds=0
                )
                context.update({"error": "Invalid input."})

        annotations_grouped_by_user = uis.get_annotations_based_on_user(
            filtered_annotations
        )
        annotations_grouped_by_question_ver = (
            uis.get_annotations_based_on_question_and_version(
                annotations_grouped_by_user
            )
        )

        annotated_and_claimed_count_dict = {
            User.objects.get(username=username): count
            for username, count in annotated_and_claimed_count_dict.items()
        }

        probation_users = list(
            ProbationPeriod.objects.values_list("user_id", flat=True)
        )

        context.update(
            {
                "annotations_exist": annotations_exist,
                "annotation_count_dict": annotated_and_claimed_count_dict,
                "annotations_grouped_by_user": annotations_grouped_by_user,
                "annotations_grouped_by_question_ver": annotations_grouped_by_question_ver,
                "annotation_filter_form": filter_form,
                "latest_updated_annotation_human_time": latest_annotation_human_time,
                "probation_users": probation_users,
            }
        )
        return render(request, "Progress/User_Info/user_info_home.html", context)

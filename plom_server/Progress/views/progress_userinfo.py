# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Elisa Pan

from django.contrib.auth.models import User
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from UserManagement.models import Quota
from UserManagement.services import ProbationService
from ..forms import AnnotationFilterForm
from ..services import UserInfoServices


class ProgressUserInfoHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()
        filter_form = AnnotationFilterForm(request.GET)

        annotations_exist = UserInfoServices.annotation_exists()
        annotated_and_claimed_count_dict = (
            UserInfoServices.get_total_annotated_and_claimed_count_by_user()
        )
        uis = UserInfoServices()
        latest_annotation_human_time = uis.get_time_of_latest_updated_annotation()
        request_time_filter_seconds = request.GET.get("time_filter_seconds")

        if filter_form.is_valid():
            time_filter_seconds = filter_form.cleaned_data["time_filter_seconds"]
            if not time_filter_seconds:
                time_filter_seconds = 0
            filtered_annotations = uis.filter_annotations_by_time_delta_seconds(
                time_delta_seconds=int(time_filter_seconds)
            )
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

        probation_users = Quota.objects.values_list("user__username", flat=True)
        probation_users_with_limits = Quota.objects.select_related("user").all()

        probation_limits = {
            prob.user.username: prob.limit for prob in probation_users_with_limits
        }

        default_probation_limit = Quota.default_limit

        # Fetch user objects for users in probation
        probation_user_objects = User.objects.filter(
            username__in=probation_users
        ).order_by("id")

        # Identify users who exceed the quota limit
        probation_service = ProbationService()
        markers_with_warnings = []
        for user in annotated_and_claimed_count_dict.keys():
            if not probation_service.can_set_quota(user):
                markers_with_warnings.append(user.username)

        context.update(
            {
                "annotations_exist": annotations_exist,
                "annotation_count_dict": annotated_and_claimed_count_dict,
                "annotations_grouped_by_user": annotations_grouped_by_user,
                "annotations_grouped_by_question_ver": annotations_grouped_by_question_ver,
                "annotation_filter_form": filter_form,
                "latest_updated_annotation_human_time": latest_annotation_human_time,
                "probation_users": probation_users,
                "default_probation_limit": default_probation_limit,
                "probation_limits": probation_limits,
                "probation_user_objects": probation_user_objects,  # Pass user objects
                "markers_with_warnings": markers_with_warnings,  # Pass markers with warnings
            }
        )
        return render(request, "Progress/User_Info/user_info_home.html", context)

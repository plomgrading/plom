# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Elisa Pan

from django.contrib.auth.models import User
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView
from UserManagement.models import Quota
from UserManagement.services import QuotaService
from ..forms import AnnotationFilterForm
from ..services import UserInfoServices


class ProgressUserInfoHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()
        filter_form = AnnotationFilterForm(request.GET)

        annotations_exist = UserInfoServices.annotation_exists()
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

        # DEPRECATED...
        _annotated_and_claimed_count_dict = (
            UserInfoServices.get_total_annotated_and_claimed_count_by_user()
        )
        annotated_and_claimed_count_dict = {
            User.objects.get(username=username): count
            for username, count in _annotated_and_claimed_count_dict.items()
        }

        usernames_with_quota = QuotaService.get_list_of_usernames_with_quotas()

        # Fetch user objects
        users_with_quota_as_objects = User.objects.filter(
            username__in=usernames_with_quota
        ).order_by("id")

        default_quota_limit = Quota.default_limit

        # Identify users who exceed the quota limit
        markers_with_warnings = []
        for user in annotated_and_claimed_count_dict.keys():
            if not QuotaService.can_set_quota(user):
                markers_with_warnings.append(user.username)

        context.update(
            {
                "annotations_exist": annotations_exist,
                "annotations_grouped_by_user": annotations_grouped_by_user,
                "annotations_grouped_by_question_ver": annotations_grouped_by_question_ver,
                "annotation_filter_form": filter_form,
                "latest_updated_annotation_human_time": latest_annotation_human_time,
                "users_with_quota": usernames_with_quota,
                "default_quota_limit": default_quota_limit,
                "users_with_quota_as_objects": users_with_quota_as_objects,
                "markers_with_warnings": markers_with_warnings,  # Pass markers with warnings
                "users_progress": UserInfoServices.get_all_user_progress(),
            }
        )
        return render(request, "Progress/User_Info/user_info_home.html", context)

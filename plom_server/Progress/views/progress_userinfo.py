# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
import time

from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import render

from Base.base_group_views import ManagerRequiredView

from Progress.services import UserInfoServices
from Mark.models import Annotation, MarkingTask


class ProgressUserInfoHome(ManagerRequiredView):
    def get(self, request):
        context = super().build_context()
        uis = UserInfoServices()

        annotations_exist = uis.annotation_exists()
        annotation_data = uis.get_total_annotations_based_on_user()

        data = MarkingTask.objects.values('assigned_user', 'question_number', 'question_version').annotate(count=Count('id')).order_by('assigned_user')
        for d in data:
            print(d)
            user = d['assigned_user']
            question_number = d['question_number']
            version_number = d['question_version']
            count = d['count']
            # user = User.objects.get(user=user)
            print(f"{user} {question_number} {version_number} {count}")

        context.update({
            "annotations_exist": annotations_exist,
            "annotation_data": annotation_data,
            "data": data,
        })
        return render(request, "Progress/User_Info/user_info_home.html", context)

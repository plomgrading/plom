import arrow
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.views import View
from braces.views import GroupRequiredMixin
from django_htmx.http import HttpResponseClientRefresh

from Connect.services import CoreUsersService
from Base.base_group_views import ManagerRequiredView


class UserPage(ManagerRequiredView):
    user_page = "UserManagement/users.html"

    def build_context(self):
        context = super().build_context()
        # core = CoreUsersService()
        users = User.objects.all()

        # login_valid = core.manager_login_status()
        # if login_valid == "valid":
        #     user_details = core.get_user_details()
        # else:
        #     user_details = []
        # context.update({"manager_status": login_valid})

        user_list = []
        for user in users:
            user_info = {}
            # if user.username in user_details:
            #     user_core_details = user_details[user.username]
            # else:
            #     user_core_details = []
            user_group = user.groups.all()[0].name
            user_info.update(
                {
                    # "details": user_core_details,
                    "obj": user,
                    "group": user_group,
                    "username": user.username,
                }
            )
            user_list.append(user_info)

        context.update({"users": user_list})
        return context

    def get(self, request):
        context = self.build_context()
        return render(request, self.user_page, context)

    def post(self, request, username):
        # core = CoreUsersService()
        # if core.manager_login_status() != "valid":
        #     return redirect("/users")

        user_to_change = User.objects.get_by_natural_key(username)
        if "changeStatus" in request.POST:
            if user_to_change.is_active:
                user_to_change.is_active = False
                # core.disable_core_user(user_to_change.username)
            else:
                user_to_change.is_active = True
                # core.enable_core_user(user_to_change.username)
            user_to_change.save()
        return redirect("/users")

    @login_required
    def enableScanners(self):
        # core = CoreUsersService()
        # if core.manager_login_status() != "valid":
        #     return redirect("/users")

        users_in_group = Group.objects.get(name="scanner").user_set.all()
        for user in users_in_group:
            user.is_active = True
            user.save()
            # core.enable_core_user(user.username)
        return redirect("/users")

    @login_required
    def disableScanners(self):
        # core = CoreUsersService()
        # if core.manager_login_status() != "valid":
        #     return redirect("/users")

        users_in_group = Group.objects.get(name="scanner").user_set.all()
        for user in users_in_group:
            user.is_active = False
            user.save()
            # core.disable_core_user(user.username)
        return redirect("/users")

    @login_required
    def enableMarkers(self):
        # core = CoreUsersService()
        # if core.manager_login_status() != "valid":
        #     return redirect("/users")

        users_in_group = Group.objects.get(name="marker").user_set.all()
        for user in users_in_group:
            user.is_active = True
            user.save()
            # core.enable_core_user(user.username)
        return redirect("/users")

    @login_required
    def disableMarkers(self):
        # core = CoreUsersService()
        # if core.manager_login_status() != "valid":
        #     return redirect("/users")

        users_in_group = Group.objects.get(name="marker").user_set.all()
        for user in users_in_group:
            user.is_active = False
            user.save()
            # core.disable_core_user(user.username)
        return redirect("/users")

    def retryConnection(self):
        """Refresh the client and check manager account status."""
        return HttpResponseClientRefresh()


class ProgressPage(ManagerRequiredView):
    progress_page = "UserManagement/progress.html"

    def build_context(self, username):
        # core = CoreUsersService()
        context = super().build_context()
        # user_details = core.get_user_details()[username]
        # login_time = arrow.get(user_details[2])
        context.update(
            {
                "username": username,
                # "last_login": login_time.humanize(),
                # "last_action": user_details[3],
                # "n_papers_id": user_details[4],
                # "n_papers_marked": user_details[5],
            }
        )
        return context

    def get(self, request, username):
        context = self.build_context(username)
        return render(request, self.progress_page, context)

    def post(self, request, username):
        return render(request, self.progress_page, username)

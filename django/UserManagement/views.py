from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.views import View

from Base.base_group_views import ManagerRequiredView


class UserPage(ManagerRequiredView):
    user_page = "UserManagement/users.html"

    def get(self, request):
        users = User.objects.all()
        context = self.build_context()
        context.update({"users": users})
        return render(request, self.user_page, context)

    def post(self, request, username):
        user_to_change = User.objects.get_by_natural_key(username)
        if "changeStatus" in request.POST:
            if user_to_change.is_active:
                user_to_change.is_active = False
            else:
                user_to_change.is_active = True
            user_to_change.save()
        return redirect("/users")

    @login_required
    def enableScanners(self):
        users_in_group = Group.objects.get(name="scanner").user_set.all()
        for user in users_in_group:
            user.is_active = True
            user.save()
        return redirect("/users")

    @login_required
    def disableScanners(self):
        users_in_group = Group.objects.get(name="scanner").user_set.all()
        for user in users_in_group:
            user.is_active = False
            user.save()
        return redirect("/users")

    @login_required
    def enableMarkers(self):
        users_in_group = Group.objects.get(name="marker").user_set.all()
        for user in users_in_group:
            user.is_active = True
            user.save()
        return redirect("/users")

    @login_required
    def disableMarkers(self):
        users_in_group = Group.objects.get(name="marker").user_set.all()
        for user in users_in_group:
            user.is_active = False
            user.save()
        return redirect("/users")


class ProgressPage(ManagerRequiredView):
    progress_page = "UserManagement/progress.html"

    def get(self, request, username):
        context = self.build_context()
        context.update({"username": username})
        return render(request, self.progress_page, context)

    def post(self, request, username):
        return render(request, self.progress_page, username)

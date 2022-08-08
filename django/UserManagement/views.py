from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.views import View

from braces.views import GroupRequiredMixin


class UserPage(LoginRequiredMixin, GroupRequiredMixin, View):
    user_page = 'UserManagement/users.html'
    group_required = [u"manager"]
    navbar_colour = '#AD9CFF'

    def get(self, request):
        user = request.user.groups.all()[0].name
        users = User.objects.all()
        context = {'navbar_colour': UserPage.navbar_colour, 'user_group':UserPage.group_required[0], 'users':users}
        return render(request, self.user_page, context)

    def post(self, request, username):
        user_to_change = User.objects.get_by_natural_key(username)
        if 'changeStatus' in request.POST:
            if user_to_change.is_active:
                user_to_change.is_active = False
            else:
                user_to_change.is_active = True
            user_to_change.save()
        return redirect('/users')

    @login_required
    def enableScanners(self):
        users_in_group = Group.objects.get(name="scanner").user_set.all()
        for user in users_in_group:
            user.is_active = True
            user.save()
        return redirect('/users')

    @login_required
    def disableScanners(self):
        users_in_group = Group.objects.get(name="scanner").user_set.all()
        for user in users_in_group:
            user.is_active = False
            user.save()
        return redirect('/users')

    @login_required
    def enableMarkers(self):
        users_in_group = Group.objects.get(name="marker").user_set.all()
        for user in users_in_group:
            user.is_active = True
            user.save()
        return redirect('/users')

    @login_required
    def disableMarkers(self):
        users_in_group = Group.objects.get(name="marker").user_set.all()
        for user in users_in_group:
            user.is_active = False
            user.save()
        return redirect('/users')


class ProgressPage(LoginRequiredMixin, GroupRequiredMixin, View):
    progress_page = 'UserManagement/progress.html'
    group_required = [u"manager"]
    navbar_colour = '#AD9CFF'

    def get(self, request, username):
        users = User.objects.all()
        context = {'navbar_colour': ProgressPage.navbar_colour, 'user_group':ProgressPage.group_required[0], 'username': username}
        return render(request, self.progress_page, context)

    def post(self, request, username):
        user_to_change = User.objects.get_by_natural_key(username)
        return render(request, self.progress_page, username)

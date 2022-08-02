from turtle import pos

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User, Group
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.views import View


class UserPage(LoginRequiredMixin, View):
    user_page = 'UserManagement/users.html'
    navbar_colour = {'admin': '#808080',
                     'manager': '#AD9CFF',
                     'marker': '#FF434B',
                     'scanner': '#0F984F'}

    def get(self, request):
        user = request.user.groups.all()[0].name
        if user in UserPage.navbar_colour:
            colour = UserPage.navbar_colour[user]
        users = User.objects.all()
        context = {'navbar_colour': colour, 'user_group':user, 'users':users}
        return render(request, self.user_page, context)


def changeStatus(request, username):
    user_to_change = User.objects.get_by_natural_key(username)
    if 'changeStatus' in request.POST:
        if user_to_change.is_active:
            user_to_change.is_active = False
        else:
            user_to_change.is_active = True
        user_to_change.save()
    return redirect('/users')

@login_required
def enableScanners(request):
    users_in_group = Group.objects.get(name="scanner").user_set.all()
    for user in users_in_group:
        user.is_active = True
        user.save()
    return redirect('/users')

@login_required
def disableScanners(request):
      users_in_group = Group.objects.get(name="scanner").user_set.all()
      for user in users_in_group:
          user.is_active = False
          user.save()
      return redirect('/users')

@login_required
def enableMarkers(request):
    users_in_group = Group.objects.get(name="marker").user_set.all()
    for user in users_in_group:
        user.is_active = True
        user.save()
    return redirect('/users')


@login_required
def disableMarkers(request):
    users_in_group = Group.objects.get(name="marker").user_set.all()
    for user in users_in_group:
        user.is_active = False
        user.save()
    return redirect('/users')


# @receiver(user_logged_in)
# def got_online(sender, user, request, **kwargs):
#     user.profile.is_online = True
#     user.profile.save()
#
#
# @receiver(user_logged_out)
# def got_offline(sender, user, request, **kwargs):
#     user.profile.is_online = False
#     user.profile.save()


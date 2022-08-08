from django.shortcuts import render
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin


# Create your views here.


class Profile(View):
    profile_page = 'Profile/profile.html'
    navbar_colour = {'admin': '#808080',
                     'manager': '#AD9CFF',
                     'marker': '#FF434B',
                     'scanner': '#0F984F'}

    def get(self, request):
        try:
            user = request.user.groups.all()[0].name
        except IndexError:
            user = None
        if user in Profile.navbar_colour:
            colour = Profile.navbar_colour[user]
        else:
            colour = '#FFFFFF'
            context = {'navbar_colour': colour, 'user_group': user}
            return render(request, self.profile_page, context)
        context = {'navbar_colour': colour, 'user_group': user}
        return render(request, self.profile_page, context, status=200)

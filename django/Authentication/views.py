from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.views.generic import View
from braces.views import GroupRequiredMixin
from bs4 import BeautifulSoup

from .services import generate_link
from .signupForm import CreateManagerForm
from Base.base_group_views import (AdminRequiredView, ManagerRequiredView)


# Create your views here.
# Set User Password
class SetPassword(View):
    template_name = 'Authentication/set_password.html'
    reset_invalid = 'Authentication/activation_invalid.html'
    set_password_complete = 'Authentication/set_password_complete.html'
    group_required = [u"manager", u"scanner", u"marker"]
    help_text = ["Your password can’t be too similar to your other personal information.",
                 "Your password must contain at least 8 characters.",
                 "Your password can’t be a commonly used password.",
                 "Your password can’t be entirely numeric."]

    def get(self, request, uidb64, token):
        try:
            uid = force_str((urlsafe_base64_decode(uidb64)))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        reset_form = SetPasswordForm(user)
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.profile.signup_confirmation = False
            user.save()
            context = {'form': reset_form, 'help_text': self.help_text}
            return render(request, self.template_name, context)
        else:
            return render(request, self.reset_invalid)

    def post(self, request, uidb64, token):
        try:
            uid = force_str((urlsafe_base64_decode(uidb64)))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is not None and default_token_generator.check_token(user, token):
            reset_form = SetPasswordForm(user, request.POST)
            if reset_form.is_valid():
                user = reset_form.save()
                user.is_active = True
                user.profile.signup_confirmation = True
                user.save()
                return render(request, self.set_password_complete)
            else:
                tri_quote = '"""'
                error_message = tri_quote + str(reset_form.errors) + tri_quote
                parsed_error = BeautifulSoup(error_message, 'html.parser')
                error = parsed_error.li.text[13:]
                context = {'form': reset_form, 'help_text': SetPassword.help_text, 'error': error}
                return render(request, self.template_name, context)
        else:
            return render(request, self.reset_invalid, status=403)


# When user enters their password successfully
class SetPasswordComplete(GroupRequiredMixin, View):
    template_name = 'Authentication/set_password_complete.html'
    login_url = 'login'

    def get(self, request):
        return render(request, self.template_name, status=200)


# login_required make sure user is log in first
class Home(LoginRequiredMixin, View):
    login_url = 'login/'
    redirect_field_name = 'login'
    home_page = 'Authentication/home.html'
    no_group_page = 'Authentication/no_group.html'
    navbar_colour = {'admin': '#808080',
                     'manager': '#AD9CFF',
                     'marker': '#FF434B',
                     'scanner': '#0F984F'}

    def get(self, request):
        try:
            user = request.user.groups.all()[0].name
        except IndexError:
            user = None
        if user in Home.navbar_colour:
            colour = Home.navbar_colour[user]
        else:
            colour = '#4000FF'
            context = {'navbar_colour': colour, 'user_group': user}
            return render(request, self.no_group_page, context)
        context = {'navbar_colour': colour, 'user_group': user}
        return render(request, self.home_page, context, status=200)


class LoginView(View):
    template_name = 'Authentication/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name)

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        else:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(
                request,
                username=username,
                password=password
            )
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                messages.info(request, 'Username or Password is incorrect!')
            return render(request, self.template_name)


# Logout User
class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')


# Signup Manager
class SignupManager(AdminRequiredView):
    template_name = 'Authentication/manager_signup.html'
    activation_link = 'Authentication/manager_activation_link.html'
    form = CreateManagerForm()

    def get(self, request):
        context = self.build_context()
        context.update({'form': SignupManager.form})
        return render(request, self.template_name, context)

    def post(self, request):
        form = CreateManagerForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()
            user.profile.email = form.cleaned_data.get('email')
            group = Group.objects.get(name='manager')
            user.groups.add(group)
            # user can't log in until the link is confirmed
            user.is_active = False
            user.save()
            link = generate_link(request, user)
            context = self.build_context()
            context.update({
                'user_email': user.profile.email,
                'link': link,
            })
            return render(request, self.activation_link, context)
        else:
            context = self.build_context()
            context.update({'form': SignupManager.form, 'error': form.errors})
            return render(request, self.template_name, context)


class SignupScannersAndMarkers(View):
    pass


class PasswordResetLinks(AdminRequiredView):
    template_name = 'Authentication/regenerative_links.html'
    activation_link = 'Authentication/manager_activation_link.html'

    def get(self, request):
        users = User.objects.all().filter(groups__name='manager').values()
        context = self.build_context()
        context.update({'users': users})
        return render(request, self.template_name, context)

    def post(self, request):
        username = request.POST.get('new_link')
        user = User.objects.get(username=username)
        link = generate_link(request, user)
        context = self.build_context()
        context.update({'link': link})
        return render(request, self.activation_link, context)


class Maintenance(Home, View):
    template_name = 'Authentication/maintenance.html'
    navbar_colour = {'admin': '#808080',
                     'manager': '#AD9CFF',
                     'marker': '#FF434B',
                     'scanner': '#0F984F'}

    def get(self, request):
        try:
            user = request.user.groups.all()[0].name
        except IndexError:
            user = None
        if user in Home.navbar_colour:
            colour = Home.navbar_colour[user]
        else:
            colour = '#4000FF'
            context = {'navbar_colour': colour, 'user_group': user}
            return render(request, self.template_name, context)
        context = {'navbar_colour': colour, 'user_group': user}
        return render(request, self.template_name, context, status=200)

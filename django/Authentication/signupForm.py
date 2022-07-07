from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

"""
This is the collection of forms to be use in a website.
Also can customize the default form that django gives us.
"""


class CreateUserForm(UserCreationForm):
    username = forms.CharField(max_length=30, help_text='Username')
    email = forms.EmailField(max_length=100, help_text='Email')

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

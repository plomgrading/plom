from braces.views import GroupRequiredMixin
from django import forms
from django.http import FileResponse
from django.shortcuts import render
from django.views import View

from django_htmx.http import HttpResponseClientRedirect


# Create your views here.
class PreparationLandingView(View):
    # group_required = [u"manager"]
    def get(self, request):
        context={}
        return render(request, "Preparation/home.html")

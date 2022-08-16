from django.shortcuts import render
from django.http import HttpResponse
from django.views import View
from django.views.generic.base import TemplateView

from braces.views import GroupRequiredMixin, LoginRequiredMixin


class ManagerRequiredView(GroupRequiredMixin, LoginRequiredMixin, TemplateView):
    login_url = "login"
    group_required = [u"manager"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["navbar_colour"] = "#AD9CFF"
        context["user_group"] = "manager"
        return context


class ConnectServerManagerView(ManagerRequiredView):
    template_name = 'Connect/connect-manager-page.html'

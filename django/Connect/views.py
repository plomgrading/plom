import requests
from requests.exceptions import ConnectionError
import json
import re

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic.base import TemplateView
from braces.views import GroupRequiredMixin, LoginRequiredMixin

from Connect.forms import CoreConnectionForm


class ManagerRequiredUtilView(GroupRequiredMixin, LoginRequiredMixin, View):
    login_url = "login"
    group_required = [u"manager"]


class ManagerRequiredTemplateView(GroupRequiredMixin, LoginRequiredMixin, TemplateView):
    login_url = "login"
    group_required = [u"manager"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["navbar_colour"] = "#AD9CFF"
        context["user_group"] = "manager"
        return context


class ConnectServerManagerView(ManagerRequiredTemplateView):
    template_name = 'Connect/connect-manager-page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CoreConnectionForm
        return context


class AttemptCoreConnectionView(ManagerRequiredUtilView):
    """Ping the core server with the URL, api version, and client version"""

    def post(self, request):
        """If the connection is valid, save core server details"""
        form_data = request.POST
        url = form_data['server_url']

        try:
            response = requests.get(
                f"{url}/Version",
                verify=False
            )

            if response.status_code == 200:
                version = response.text
                print(version)
                server_version = re.search(r'\d\.\d\.\d\.(dev)?', version).group(0)
                api = re.search(r'\d+$', version).group(0)
                
                return HttpResponse(f'<p>Connection successful! Server version: {server_version}, API: {api}</p>')

            else:
                return HttpResponse('<p>Connection not successful</p>')
        except ConnectionError:
            return HttpResponse('<p>Failed to establish a connection. Is the server running?</p>')

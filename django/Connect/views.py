import requests
from requests.exceptions import ConnectionError
import json
import re

from plom.plom_exceptions import PlomConnectionError

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic.base import TemplateView
from braces.views import GroupRequiredMixin, LoginRequiredMixin

from Connect.services import CoreConnectionService
from Connect.forms import CoreConnectionForm
from .models import CoreServerConnection


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
        port_number = form_data['port_number']

        core = CoreConnectionService()

        try:
            version_string = core.validate_url(url, port_number)

            if version_string:
                core.save_connection_info(url, port_number, version_string)
                version = core.get_client_version()
                api = core.get_api()
                return HttpResponse(f'<p id="result">Connection successful! Server version: {version}, API: {api}</p>')

        except PlomConnectionError as e:
            print(e)
            return HttpResponse(f'<p id="result" style="color: red;">Unable to connect to Plom Classic. Is the server running?</p>')
        

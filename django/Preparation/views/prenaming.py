from django.shortcuts import render
from django_htmx.http import HttpResponseClientRedirect

from Preparation.services import PrenameSettingService
from Preparation.views.needs_manager_view import ManagerRequiredBaseView


class PrenamingView(ManagerRequiredBaseView):
    def build_context(self):
        pss = PrenameSettingService()
        return {
            "prenaming_enabled": pss.get_prenaming_setting(),
        }

    def get(self, request):
        context = self.build_context()
        return render(request, "Preparation/prenaming_manage.html", context)

    def post(self, request):
        pss = PrenameSettingService()
        pss.set_prenaming_setting(True)
        return HttpResponseClientRedirect("/preparation/prename")

    def delete(self, request):
        pss = PrenameSettingService()
        pss.set_prenaming_setting(False)
        return HttpResponseClientRedirect("/preparation/prename")

from braces.views import GroupRequiredMixin
from django.shortcuts import render
from django.views import View

from django_htmx.http import HttpResponseClientRedirect

from Preparation.services import PrenameSettingService, PrenameClasslistCSVService


class PrenamingView(View):
    # group_required = [u"manager"]
    def build_context(self):
        pss = PrenameSettingService()
        pcs = PrenameClasslistCSVService()
        return {
            "prenaming_enabled": pss.get_prenaming_setting(),
            "csv_exists": pcs.is_there_a_classlist(),
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

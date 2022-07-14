from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse
from .. import services


class TestSpecResetView(View):
    def post(self, request):
        services.clear_questions()
        services.delete_pdf()
        services.reset_spec()
        services.reset_progress()
        return HttpResponseRedirect(reverse('names'))
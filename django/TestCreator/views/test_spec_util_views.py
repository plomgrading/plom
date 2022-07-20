import toml
from django.http import HttpResponse, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from .. import services
from . import BaseTestSpecUtilView, BaseTestSpecTemplateView


class TestSpecResetView(BaseTestSpecUtilView):
    def post(self, request):
        services.clear_questions()
        services.delete_pdf()
        services.reset_spec()
        services.reset_progress()
        return HttpResponseRedirect(reverse('names'))


class TestSpecGenTomlView(BaseTestSpecUtilView):
    def dispatch(self, request, **kwargs):
        if not services.progress_is_everything_complete():
            raise PermissionDenied('Specification not completed yet.')

        return super().dispatch(request, **kwargs)

    def get(self, request):
        spec_dict = services.generate_spec_dict()
        toml_file = toml.dumps(spec_dict)

        response = HttpResponse(toml_file)
        response['mimetype'] = 'text/plain'
        response['Content-Disposition'] = 'attachment;'
        return response


class TestSpecDownloadView(BaseTestSpecTemplateView):
    template_name = 'TestCreator/test-spec-download-page.html'

    def dispatch(self, request, **kwargs):
        if not services.progress_is_everything_complete():
            raise PermissionDenied('Specification not completed yet.')

        return super().dispatch(request, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data('download')


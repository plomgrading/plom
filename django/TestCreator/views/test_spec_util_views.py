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
            return HttpResponseRedirect(reverse('validate'))

        return super().dispatch(request, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data('download')


class TestSpecSubmitView(BaseTestSpecTemplateView):
    template_name = 'TestCreator/test-spec-submit-page.html'

    def dispatch(self, request,**kwargs):
        if not services.progress_is_everything_complete():
            raise PermissionDenied('Specification not completed yet.')

        return super().dispatch(request, **kwargs)

    def get_context_data(self, **kwargs):
        context =  super().get_context_data('submit')
        pages = services.get_page_list()
        num_questions = services.get_num_questions()

        context['num_pages'] = len(pages)
        context['num_versions'] = services.get_num_versions()
        context['num_questions'] = num_questions
        context['id_page'] = services.get_id_page_number()
        context['dnm_pages'] = ', '.join(f'p. {i}' for i in services.get_dnm_page_numbers())
        context['total_marks'] = services.get_total_marks()

        context['questions'] = []
        for i in range(num_questions):
            question = {}

            # TODO: question get is 1-indexed??
            question['pages'] = ', '.join(f'p. {i}' for i in services.get_question_pages(i+1))
            question['label'] = services.get_question_label(i+1)
            question['mark'] = services.get_question_marks(i+1)
            question['shuffle'] = services.get_question_fix_or_shuffle(i+1)
            context['questions'].append(question)
        return context


class TestSpecLaunchView(BaseTestSpecTemplateView):
    template_name = 'TestCreator/test-spec-launch-page.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data('launch')

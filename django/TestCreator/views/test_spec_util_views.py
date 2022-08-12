import toml
from django.http import HttpResponse, HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from . import BaseTestSpecUtilView, BaseTestSpecTemplateView
from ..services import TestSpecService, ReferencePDFService, TestSpecProgressService, TestSpecGenerateService


class TestSpecResetView(BaseTestSpecUtilView):
    def post(self, request):
        spec = TestSpecService()
        ref_service = ReferencePDFService(spec)
        spec.clear_questions()
        ref_service.delete_pdf()
        spec.reset_specification()
        return HttpResponseRedirect(reverse('names'))


class TestSpecGenTomlView(BaseTestSpecUtilView):
    def dispatch(self, request, **kwargs):
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)
        if not prog.is_everything_complete():
            raise PermissionDenied('Specification not completed yet.')

        return super().dispatch(request, **kwargs)

    def get(self, request):
        spec = TestSpecService()
        gen = TestSpecGenerateService(spec)
        spec_dict = gen.generate_spec_dict()
        toml_file = toml.dumps(spec_dict)

        response = HttpResponse(toml_file)
        response['mimetype'] = 'text/plain'
        response['Content-Disposition'] = 'attachment;'
        return response


class TestSpecDownloadView(BaseTestSpecTemplateView):
    template_name = 'TestCreator/test-spec-download-page.html'

    def dispatch(self, request, **kwargs):
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)
        if not prog.is_everything_complete():
            return HttpResponseRedirect(reverse('validate'))

        return super().dispatch(request, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data('download')


class TestSpecSubmitView(BaseTestSpecTemplateView):
    template_name = 'TestCreator/test-spec-submit-page.html'

    def dispatch(self, request,**kwargs):
        spec = TestSpecService()
        prog = TestSpecProgressService(spec)
        if not prog.is_everything_complete():
            raise PermissionDenied('Specification not completed yet.')

        return super().dispatch(request, **kwargs)

    def get_context_data(self, **kwargs):
        context =  super().get_context_data('submit')
        spec = TestSpecService()
        pages = spec.get_page_list()
        num_questions = spec.get_n_questions()

        context['num_pages'] = len(pages)
        context['num_versions'] = spec.get_n_versions()
        context['num_questions'] = num_questions
        context['id_page'] = spec.get_id_page_number()
        context['dnm_pages'] = ', '.join(f'p. {i}' for i in spec.get_dnm_page_numbers())
        context['total_marks'] = spec.get_total_marks()

        context['questions'] = []
        for i in range(num_questions):
            question = {}

            question['pages'] = ', '.join(f'p. {j}' for j in spec.get_question_pages(i+1))
            if i+1 in spec.questions:
                q_obj = spec.questions[i+1].get_question()
                question['label'] = q_obj.label
                question['mark'] = q_obj.mark
                question['shuffle'] = spec.questions[i+1].get_question_fix_or_shuffle()
            else:
                question['label'] = ''
                question['mark'] = ''
                question['shuffle'] = ''
            context['questions'].append(question)
        return context


class TestSpecLaunchView(BaseTestSpecTemplateView):
    template_name = 'TestCreator/test-spec-launch-page.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data('launch')

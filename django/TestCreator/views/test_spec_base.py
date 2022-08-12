import pathlib
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from braces.views import LoginRequiredMixin, GroupRequiredMixin
from ..services import TestSpecService, TestSpecProgressService, ReferencePDFService
from .. import models


class BaseTestSpecFormView(GroupRequiredMixin, FormView):
    login_url = 'login'
    group_required = u"manager"
    raise_exception = True

    def get_context_data(self, page_name, **kwargs):
        context = super().get_context_data(**kwargs)
        spec = TestSpecService()

        context['long_name'] = spec.get_long_name()
        context['short_name'] = spec.get_short_name()
        context['curr_page'] = page_name
        context['questions'] = [i for i in range(spec.get_n_questions())]
        context['n_questions'] = spec.get_n_questions()

        progress = TestSpecProgressService(spec)
        context['completed'] = progress.get_progress_dict()
        context['navbar_colour'] = '#AD9CFF'
        context['user_group'] = 'manager'
        return context

    def form_valid(self, form, on_validate_page=False):
        """Set the validation page to unsubmitted"""
        if not on_validate_page:
            spec = TestSpecService()
            spec.unvalidate()

        return super().form_valid(form)


class BaseTestSpecFormPDFView(BaseTestSpecFormView):
    pdf = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        spec = TestSpecService()
        ref_service = ReferencePDFService(spec)

        try:
            self.pdf = ref_service.get_pdf()
            kwargs['num_pages'] = self.pdf.num_pages
        except RuntimeError:
            kwargs['num_pages'] = 0

        return kwargs

    def get_context_data(self, page_name, **kwargs):
        context = super().get_context_data(page_name, **kwargs)

        if self.pdf:
            spec = TestSpecService()
            ref_service = ReferencePDFService(spec)
            pages = ref_service.create_page_thumbnail_list()
            context['thumbnails'] = pages
            context['pages'] = spec.get_page_list()
            context['num_pages'] = len(spec.get_page_list())

        return context


class BaseTestSpecUtilView(GroupRequiredMixin, View):
    group_required = [u"manager"]
    raise_exception = True


class BaseTestSpecTemplateView(GroupRequiredMixin, TemplateView):
    group_required = [u"manager"]
    raise_exception = True

    def get_context_data(self, page_name, **kwargs):
        context = super().get_context_data(**kwargs)
        spec = TestSpecService()

        context['long_name'] = spec.get_long_name()
        context['short_name'] = spec.get_short_name()
        context['curr_page'] = page_name
        context['questions'] = [i for i in range(spec.get_n_questions())]
        
        context['navbar_colour'] = '#AD9CFF'
        context['user_group'] = 'manager'

        progress = TestSpecProgressService(spec)
        context['completed'] = progress.get_progress_dict()
        return context

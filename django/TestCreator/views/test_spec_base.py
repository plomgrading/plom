import pathlib
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from braces.views import LoginRequiredMixin, GroupRequiredMixin
from .. import services
from .. import models


class BaseTestSpecFormView(GroupRequiredMixin, FormView):
    login_url = 'login'
    group_required = u"manager"
    raise_exception = True

    def get_context_data(self, page_name, **kwargs):
        context = super().get_context_data(**kwargs)
        context['long_name'] = services.get_long_name()
        context['short_name'] = services.get_short_name()
        context['curr_page'] = page_name
        context['questions'] = [i for i in range(services.get_num_questions())]

        context['completed'] = services.get_progress_dict()
        context['navbar_colour'] = '#AD9CFF'
        context['user_group'] = 'manager'
        return context


class BaseTestSpecFormPDFView(BaseTestSpecFormView):
    pdf = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # we're going to have to load the PDF in this method for now
        saved_pdfs = models.ReferencePDF.objects.all()
        if len(saved_pdfs) > 1:
            raise RuntimeError('Multiple PDFs saved in database!')
        elif len(saved_pdfs) == 1:
            self.pdf = saved_pdfs[0]
            kwargs['num_pages'] = self.pdf.num_pages
        else:
            kwargs['num_pages'] = 0
        return kwargs

    def get_context_data(self, page_name, **kwargs):
        context = super().get_context_data(page_name, **kwargs)

        if self.pdf:
            pages = services.create_page_thumbnail_list(self.pdf)
            context['thumbnails'] = pages
            context['pages'] = services.get_page_list()
            context['num_pages'] = len(services.get_page_list())

        return context


class BaseTestSpecUtilView(GroupRequiredMixin, View):
    group_required = [u"manager"]
    raise_exception = True


class BaseTestSpecTemplateView(GroupRequiredMixin, TemplateView):
    group_required = [u"manager"]
    raise_exception = True

    def get_context_data(self, page_name, **kwargs):
        context = super().get_context_data(**kwargs)
        context['long_name'] = services.get_long_name()
        context['short_name'] = services.get_short_name()
        context['curr_page'] = page_name
        context['questions'] = [i for i in range(services.get_num_questions())]
        
        context['navbar_colour'] = '#AD9CFF'
        context['user_group'] = 'manager'

        context['completed'] = services.get_progress_dict()
        return context

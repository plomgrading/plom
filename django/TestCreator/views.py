import re
import pathlib
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.forms import forms, formset_factory
from braces.views import GroupRequiredMixin, LoginRequiredMixin
from . import forms
from . import models
from . import services

# TODO: docstrings!! On the methods
# Top-level blurb for each class, type hints for methods

class BaseTestSpecFormView(LoginRequiredMixin, GroupRequiredMixin, FormView):
    TEMPLATES = pathlib.Path('test_creator')
    login_url = 'login'
    group_required = [u"manager"]

    def get_context_data(self, page_name, **kwargs):
        context = super().get_context_data(**kwargs)
        context['long_name'] = services.get_long_name()
        context['short_name'] = services.get_short_name()
        context['curr_page'] = page_name
        context['questions'] = [i for i in range(services.get_num_questions())]

        context['completed'] = {}

        # did we complete the 'names' page?
        if context['long_name'] and context['short_name']:
            context['completed']['names'] = True

        # or the reference pdf page?
        saved_pdfs = models.ReferencePDF.objects.all()
        if len(saved_pdfs) > 0:
            context['completed']['upload'] = True

        # or select the ID page?
        id_page = services.get_id_page_number()
        if id_page:
            context['completed']['id_page'] = True

        # or the questions page?
        total_marks = services.get_total_marks()
        if total_marks and context['questions']:
            context['completed']['questions_page'] = True

        # or the question details?
        context['completed']['question_list'] = []
        for i in range(len(context['questions'])):
            if services.is_question_completed(i+1):
                context['completed']['question_list'].append(i+1)

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


class TestSpecCreatorNamesPage(BaseTestSpecFormView):
    template_name = 'test_creator/test-spec-names-page.html'
    form_class = forms.TestSpecNamesForm

    def get_context_data(self, **kwargs):
        return super().get_context_data('names', **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['long_name'] = services.get_long_name()
        initial['short_name'] = services.get_short_name()
        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data
        long_name = form_data['long_name']
        short_name = form_data['short_name']
        services.set_long_name(long_name)
        services.set_short_name(short_name)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('upload')


class TestSpecCreatorVersionsRefPDFPage(BaseTestSpecFormView):
    template_name = 'test_creator/test-spec-upload-pdf.html'
    form_class = forms.TestSpecVersionsRefPDFForm
    slug = None

    def get_context_data(self, **kwargs):
        return super().get_context_data('upload', **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['versions'] = services.get_num_versions()
        initial['num_to_produce'] = services.get_num_to_produce()
        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data

        n_versions = form_data['versions']
        services.set_num_versions(n_versions)

        n_to_produce = form_data['num_to_produce']
        services.set_num_to_produce(n_to_produce)

        self.num_pages = form_data['num_pages']
        self.slug = slugify(re.sub('.pdf$', '', str(form_data['pdf'])))

        # make sure there's only one PDF saved in the database at one time
        saved_pdfs = models.ReferencePDF.objects.all()
        if len(saved_pdfs) > 0:
            saved_pdfs.delete()

        pdf = services.create_pdf(self.slug, self.num_pages, self.request.FILES['pdf'])
        services.get_and_save_pdf_images(pdf)
        services.set_pages(pdf)
        
        # when we upload a new PDF, clear questions
        services.clear_questions()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('id_page')


class TestSpecCreatorIDPage(BaseTestSpecFormPDFView):
    template_name = 'test_creator/test-spec-id-page.html'
    form_class = forms.TestSpecIDPageForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data('id_page', **kwargs)
        
        context['x_data'] = services.get_id_page_alpine_xdata()
        context['pages'] = services.get_pages_for_id_select_page()

        return context

    def form_valid(self, form):
        form_data = form.cleaned_data
        for field in form_data:
            print(f'{field}: {form_data[field]}')

        # save ID page
        services.clear_id_page()
        for key, value in form_data.items():
            if 'page' in key and value == True:
                idx = int(re.sub('\D', '', key))
                services.set_id_page(idx)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('questions')


class TestSpecCreatorQuestionsPage(BaseTestSpecFormView):
    template_name = 'test_creator/test-spec-questions-marks-page.html'
    form_class = forms.TestSpecQuestionsMarksForm

    def get_context_data(self, **kwargs):
        return super().get_context_data('questions', **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if services.get_num_questions() > 0:
            initial['questions'] = services.get_num_questions()
        if services.get_total_marks() > 0:
            initial['total_marks'] = services.get_total_marks()

        return initial

    def form_valid(self, form):
        form_data = form.cleaned_data

        services.clear_questions()

        services.set_num_questions(form_data['questions'])
        services.set_total_marks(form_data['total_marks'])
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('q_detail', args=(1,))


class TestSpecCreatorQuestionDetailPage(BaseTestSpecFormPDFView):
    template_name = 'test_creator/test-spec-question-detail-page.html'
    form_class = forms.TestSpecQuestionForm

    def get_initial(self):
        initial = super().get_initial()
        question_id = self.kwargs['q_idx']
        if services.question_exists(question_id):
            question = services.get_question(question_id)
            initial['label'] = question.label
            initial['mark'] = question.mark
            initial['shuffle'] = question.shuffle
        else:
            initial['label'] = f"Q{question_id}"
            if services.get_num_versions() > 1:
                initial['shuffle'] = 'S'
            else:
                initial['shuffle'] = 'F'
        return initial

    def get_context_data(self, **kwargs):
        question_id = self.kwargs['q_idx']
        context = super().get_context_data(f'question_{question_id}', **kwargs)
        context['question_id'] = question_id
        context['prev_id'] = question_id-1
        context['total_marks'] = services.get_total_marks()
        context['n_versions'] = services.get_num_versions()

        context['x_data'] = services.get_question_detail_page_alpine_xdata(question_id)
        context['pages'] = services.get_pages_for_question_detail_page(question_id)

        return context

    def form_valid(self, form):
        form_data = form.cleaned_data
        question_id = self.kwargs['q_idx']

        # save the question to the database
        label = form_data['label']
        mark = form_data['mark']
        shuffle = form_data['shuffle']

        services.create_or_replace_question(question_id, label, mark, shuffle)

        # save the question pages
        question_ids = []
        for key, value in form_data.items():
            if 'page' in key and value == True:
                idx = int(re.sub('\D', '', key))
                question_ids.append(idx)
        services.set_question_pages(question_ids, question_id)
        
        return super().form_valid(form)

    def get_success_url(self):
        question_id = self.kwargs['q_idx']
        num_questions = services.get_num_questions()
        if question_id == num_questions:
            return reverse('dnm_page')
        else:
            return reverse('q_detail', args=(question_id + 1,))


class TestSpecCreatorDNMPage(BaseTestSpecFormPDFView):
    template_name = 'test_creator/test-spec-do-not-mark-page.html'
    form_class = forms.TestSpecPDFSelectForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data('dnm_page', **kwargs)
        context['num_questions'] = services.get_num_questions()
        context['x_data'] = services.get_dnm_page_alpine_xdata()
        context['pages'] = services.get_pages_for_dnm_select_page()
        return context

    def form_valid(self, form):
        form_data = form.cleaned_data

        # save do not mark pages
        dnm_idx = []
        for key, value in form_data.items():
            if 'page' in key and value == True:
                idx = int(re.sub('\D', '', key))
                dnm_idx.append(idx)
        services.set_do_not_mark_pages(dnm_idx)


        return super().form_valid(form)

    def get_success_url(self):
        return reverse('summary')


class TestSpecSummaryView(BaseTestSpecFormView):
    template_name = 'test_creator/test-spec-summary-page.html'
    form_class = forms.TestSpecSummaryForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data('summary', **kwargs)
        pages = services.get_page_list()
        num_questions = services.get_num_questions()

        context['num_pages'] = len(pages)
        context['num_versions'] = services.get_num_versions()
        context['num_questions'] = num_questions
        context['id_page'] = services.get_id_page_number()
        context['dnm_pages'] = ', '.join(str(i) for i in services.get_dnm_page_numbers())
        context['total_marks'] = services.get_total_marks()

        context['questions'] = []
        for i in range(num_questions):
            question = {}

            # TODO: question get is 1-indexed??
            question['pages'] = ', '.join(str(i) for i in services.get_question_pages(i+1))
            question['label'] = services.get_question_label(i+1)
            question['mark'] = services.get_question_marks(i+1)
            question['shuffle'] = services.get_question_fix_or_shuffle(i+1)
            context['questions'].append(question)
        return context


def test_spec_reset_view_pdf(request):
    if request.method == 'POST':
        services.clear_questions()
        services.delete_pdf()
        services.reset_spec()
        return HttpResponseRedirect(reverse('names'))
        

def test_spec_creator_view_pdf(request, num_pages):

    return render(request, 'test_creator/test-spec-view-pages.html', context={
        'long_name': 'Sample test 102', 
        'short_name': 'st102',
        'pages': [' ' for i in range(num_pages)],
        })


def test_spec_creator_image_view(request, slug):

    pdf = models.ReferencePDF.objects.get(filename_slug=slug)
    pages = services.create_page_thumbnail_list(pdf)

    return render(request, 'test_creator/test-spec-view-pages-thumbnails.html', context={
        'long_name': 'Sample test 102', 
        'short_name': 'st102',
        'pages': pages,
        })


def test_render(request):
    return render(request, 'test_creator/base-test-spec-2col.html')
from select import select
from django import forms
from django.forms import ModelForm
import fitz
import re
from django.core.exceptions import ValidationError
from . import models
from . import services


class TestSpecNamesForm(forms.Form):
    long_name = forms.CharField(
        max_length=100, 
        label="Long name:", 
        help_text="The full name of the test, for example \"Maths101 Midterm 2\"",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    short_name = forms.CharField(
        max_length=50, 
        label="Name:", 
        help_text="The short name of the test, for example \"m101mt2\"",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    versions = forms.IntegerField(
        label='Number of versions:',
        help_text="For shuffling questions over multiple test papers.",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1})
    )


class TestSpecVersionsRefPDFForm(forms.Form):
    pdf = forms.FileField(
        allow_empty_file=False,
        max_length=100,
        label='Reference PDF:',
        help_text='Upload a PDF of a test version for rendering page thumbnails.',
        widget=forms.FileInput(attrs={'accept': 'application/pdf', 'class': 'form-control'})
    )

    def clean(self):
        data = self.cleaned_data
        pdf = data['pdf']
        
        # validate that file is a PDF
        pdf_doc = fitz.open(stream=pdf.read())
        if 'PDF' not in pdf_doc.metadata['format']:
            raise ValidationError('File is not a valid PDF.')

        data['num_pages'] = pdf_doc.page_count

        return data


class TestSpecPDFSelectForm(forms.Form):
    def __init__(self, *args, **kwargs):
        num_pages = kwargs.pop('num_pages')
        super().__init__(*args, **kwargs)

        for i in range(num_pages):
            self.fields.update({
                f'page{i}': forms.BooleanField(
                    required=False,
                    widget=forms.HiddenInput(attrs={'x-bind:value': f'page{i}selected'})
                    )
            })


class TestSpecIDPageForm(TestSpecPDFSelectForm):
    def clean(self):
        data = self.cleaned_data
        selected_pages = [key for key in data.keys() if data[key]]
        if len(selected_pages) > 1:
            raise ValidationError('Test can have only one ID page.')

        return data


class TestSpecQuestionsMarksForm(forms.Form):
    questions = forms.IntegerField(
        label='Number of questions:',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    total_marks = forms.IntegerField(
        label='Total marks:',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        data = self.cleaned_data

        if data['total_marks'] < data['questions']:
            raise ValidationError('Number of questions should not exceed the total marks.')

        if data['questions'] > 50:
            # TODO: be nicer
            raise ValidationError('Your test is too long!')


class TestSpecQuestionForm(TestSpecPDFSelectForm):
    label = forms.CharField(
        max_length=15,
        label='Label:',
        help_text="Question label. Default Q(i)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    mark = forms.IntegerField(
        label='Mark:',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    shuffle = forms.ChoiceField(
        label='Shuffle:',
        choices = models.SHUFFLE_CHOICES,
        help_text="Shuffle over test versions, or use first version",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, **kwargs):
        self.question_marks = kwargs.pop('q_marks')
        super().__init__(*args, **kwargs)

    def clean(self):
        data = self.cleaned_data

        # Are the marks less than the test's total marks?
        if data['mark'] > services.get_total_marks():
            raise ValidationError("Question cannot have more marks than the test.")

        # Are the marks less than the total available marks?
        available = services.get_available_marks(self.question_marks)
        if data['mark'] > available:
            raise ValidationError(f"Question cannot have more than {available} marks.")

        selected_pages = []
        for key, value in data.items():
            if 'page' in key and value:
                selected_pages.append(int(re.sub('\D', '', key)))
        selected_pages = sorted(selected_pages)

        # Was at least one page selected?
        if len(selected_pages) < 1:
            raise ValidationError('At least one page must be selected.')

        # Are the selected pages next to each other?
        for i in range(len(selected_pages)-1):
            curr = selected_pages[i]
            next = selected_pages[i+1]

            if next - curr > 1:
                raise ValidationError('Question pages must be consecutive.')


class TestSpecSummaryForm(forms.Form):
    def clean(self):
        """
        Things to check:

        Is there a long name and a short name?

        Are there test versions, num_to_produce, and a reference PDF?

        Is there an ID page?

        Are there questions?

        Do all the questions have pages attached?

        Do all the questions have the relevant fields?

        Are all the pages selected by something?
        """

        progress_dict = services.get_progress_dict()
        
        if not progress_dict['names']:
            raise ValidationError('Test needs a long name, short name, and number of versions.')

        if not progress_dict['upload']:
            raise ValidationError('Test needs a reference PDF.')

        if not progress_dict['id_page']:
            raise ValidationError('Test needs an ID page.')

        if not progress_dict['questions_page']:
            raise ValidationError('Test needs questions.')

        questions = progress_dict['question_list']
        print(questions)
        for i in range(len(questions)):
            if not questions[i]:
                raise ValidationError(f'Question {i+1} is incomplete.')

        pages = services.get_page_list()
        for i in range(len(pages)):
            cur_page = pages[i]
            if not cur_page['id_page'] and not cur_page['dnm_page'] and not cur_page['question_page']:
                raise ValidationError(f'Page {i+1} has not been assigned. Did you mean to make it a do-not-mark page?')

        marks_for_all_questions = services.get_total_assigned_marks
        if marks_for_all_questions != services.get_total_marks:
            raise RuntimeError(f'There are {services.get_total_marks} marks assigned to the test, but {marks_for_all_questions} marks in total assigned to the questions.')

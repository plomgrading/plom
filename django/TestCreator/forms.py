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
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    short_name = forms.CharField(
        max_length=50, 
        label="Name:", 
        help_text="The short name of the test, for example \"m101mt2\"",
        widget=forms.TextInput(attrs={'class': 'form-control'}))


class TestSpecVersionsRefPDFForm(forms.Form):
    versions = forms.IntegerField(
        label='Number of versions:',
        help_text="For shuffling questions over multiple test papers.",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1})
    )

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
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    total_marks = forms.IntegerField(
        label='Total marks:',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        data = self.cleaned_data
        if data['total_marks'] < data['questions']:
            raise ValidationError('Number of questions should not exceed the total marks.')


class TestSpecQuestionForm(TestSpecPDFSelectForm):
    label = forms.CharField(
        max_length=15,
        label='Label:',
        help_text="Question label. Default Q(i)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    mark = forms.IntegerField(
        label='Mark:',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    shuffle = forms.ChoiceField(
        label='Shuffle:',
        choices = models.SHUFFLE_CHOICES,
        help_text="Shuffle over test versions, or use first version",
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )

    # def clean(self):
    #     data = self.cleaned_data

    #     # are the selected pages next to each other?
    #     pages = [int(re.sub('\D', '', key)) for key in data.keys() if 'page' in key]
        
    #     seen_first_selected = False
    #     seen_next_deselected = False
    #     for i in range(1, len(pages)):  # We don't need to worry about the first page
    #         if data[f'page{i}'] and seen_next_deselected:
    #             raise ValidationError('Question pages must be consecutive.')
    #         elif data[f'page{i}'] and not seen_first_selected:
    #             seen_first_selected = 

    def clean(self):
        data = self.cleaned_data

        # Are the marks less than the test's total marks?
        if data['mark'] > services.get_total_marks():
            raise ValidationError("Question cannot have more marks than the test.")

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
    pass

"""
Wizard forms
"""

class TestSpecWizardNamesForm(forms.Form):
    name = forms.CharField(max_length=50, label='Name', help_text="The \"short name\" for the test, for example \"m101mt2\"")
    long_name = forms.CharField(max_length=100, label='Long name', help_text="The full name of the test, for example \"Maths101 Midterm 2\"")
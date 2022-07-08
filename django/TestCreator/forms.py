from django import forms
from django.forms import ModelForm
import fitz
from django.core.exceptions import ValidationError
from . import models


class TestSpecNamesForm(forms.Form):
    long_name = forms.CharField(
        max_length=100, 
        label="Long name:", 
        help_text="The full name of the test, for example \"Maths101 Midterm 2\"",
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    short_name = forms.CharField(
        max_length=50, 
        label="Name:", 
        help_text="The short name for the test, for example \"m101mt2\"",
        widget=forms.TextInput(attrs={'class': 'form-control'}))


class SimpleUploadFormPDF(forms.Form):
    pdf = forms.FileField(
        allow_empty_file=False,
        max_length=100,
        label='Reference PDF',
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


class TestSpecSummaryForm(forms.Form):
    pass

"""
Wizard forms
"""

class TestSpecWizardNamesForm(forms.Form):
    name = forms.CharField(max_length=50, label='Name', help_text="The \"short name\" for the test, for example \"m101mt2\"")
    long_name = forms.CharField(max_length=100, label='Long name', help_text="The full name of the test, for example \"Maths101 Midterm 2\"")
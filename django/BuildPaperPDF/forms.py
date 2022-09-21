from django import forms
from django.core.exceptions import ValidationError


class BuildNumberOfPDFsForm(forms.Form):
    pdfs = forms.IntegerField(
        label="Number of PDFs to print:",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    )

    def clean(self):
        data = self.cleaned_data
        min_PDFs = 1

        if data["pdfs"] < min_PDFs:
            raise ValidationError("Cannot print less than 1 PDF file!")

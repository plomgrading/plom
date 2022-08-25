import glob
import os
from pathlib import Path
from wsgiref.util import FileWrapper

from django.shortcuts import render
from django.views.generic import View
from braces.views import LoginRequiredMixin, GroupRequiredMixin

from BuildPaperPDF.forms import BuildNumberOfPDFsForm
from django.http import FileResponse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.core.files import File
from io import BytesIO

from Connect.services import CoreConnectionService

from .services import (generate_pdf, BuildPapersService)
from .models import Task


# Create your views here.


class BuildPaperPDFs(LoginRequiredMixin, GroupRequiredMixin, View):
    template_name = 'BuildPaperPDF/build_paper_pdfs.html'
    login_url = "login"
    group_required = ["manager"]
    navbar_colour = "#AD9CFF"
    form = BuildNumberOfPDFsForm()

    def get(self, request):
        context = {'navbar_colour': self.navbar_colour, 'user_group': self.group_required[0],
                   'form': self.form, 'message': ''}
        return render(request, self.template_name, context)

    def post(self, request):
        form = BuildNumberOfPDFsForm(request.POST)
        if form.is_valid():
            # number_of_pdfs = int(request.POST.get('pdfs'))
            paper_PDFs = []

            # for num in range(1, number_of_pdfs + 1):
            #     ccs = CoreConnectionService()
            #     BuildPapersService.build_single_paper(num, ccs)

            path = settings.BASE_DIR / 'papersToPrint'
            path_list = sorted(Path(path).glob('*.pdf'))
            for pdf in path_list:
                paper_PDFs.append(str(pdf.name))

            message = 'Your pdf finished building! See below.'

            context = {'navbar_colour': self.navbar_colour, 'user_group': self.group_required[0],
                       'form': self.form, 'message': message, 'paper_pdfs': paper_PDFs}
            return render(request, self.template_name, context)


class GetPDFFile(View):

    def get(self, request):
        test_pdf_file = Task.objects.all()[0].pdf_file
        pdf = SimpleUploadedFile('paper.pdf', test_pdf_file, content_type='application/pdf')

        return FileResponse(pdf)

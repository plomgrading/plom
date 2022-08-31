import pathlib

from django.shortcuts import render
from django.views.generic import View
from braces.views import LoginRequiredMixin, GroupRequiredMixin

from BuildPaperPDF.forms import BuildNumberOfPDFsForm
from django.http import FileResponse
from django.http import HttpResponse
from django.core.files.uploadedfile import SimpleUploadedFile

from Connect.services import CoreConnectionService
from Preparation.services import PQVMappingService

from .services import (BuildPapersService, RenamePDFFile)
from .models import PDFTask


# Create your views here.


class BuildPaperPDFs(LoginRequiredMixin, GroupRequiredMixin, View):
    template_name = 'BuildPaperPDF/build_paper_pdfs.html'
    login_url = "login"
    group_required = ["manager"]
    navbar_colour = "#AD9CFF"
    form = BuildNumberOfPDFsForm()

    def get(self, request):
        # bps = BuildPapersService()
        # pqvs = PQVMappingService()
        # qvmap = pqvs.get_pqv_map_dict()
        # num_pdfs = len(qvmap)
        num_pdfs = 1

        # n_tasks = bps.get_n_tasks()
        n_tasks = 1
        if n_tasks > 0:
            pdfs_staged = True
        else:
            pdfs_staged = False

        context = {'navbar_colour': self.navbar_colour, 'user_group': self.group_required[0],
                   'form': self.form, 'message': '', 'zip_disabled': True, 'num_pdfs': num_pdfs,
                   'pdfs_staged': pdfs_staged}
        return render(request, self.template_name, context)

    def post(self, request):
        bps = BuildPapersService()
        core = CoreConnectionService()
        spec = core.get_core_spec()
        pqvs = PQVMappingService()
        qvmap = pqvs.get_pqv_map_dict()
        num_pdfs = len(qvmap)

        bps.clear_tasks()
        bps.build_n_papers(num_pdfs, spec, qvmap)

        task_objects = PDFTask.objects.all()
        Rename = RenamePDFFile()

        tasks_paper_number = []
        tasks_pdf_file_path = []
        tasks_status = []

        for task in task_objects:
            tasks_paper_number.append(task.paper_number)
            tasks_pdf_file_path.append(Rename.get_PDF_name(task.pdf_file_path))
            tasks_status.append(task.status)
        message = f'Progress: 0 papers of {num_pdfs} built. (0%)'
        context = {
            'navbar_colour': self.navbar_colour,
            'user_group': self.group_required[0],
            'form': self.form, 'message': message,
            'tasks': zip(task_objects, tasks_pdf_file_path),
            'zip_disabled': True,
        }
        return render(request, self.template_name, context)


class UpdatePDFTable(View):
    """Get an updated pdf-building-progress table"""
    def get(self, request):
        task_objects = PDFTask.objects.all()
        bps = BuildPapersService()
        Rename = RenamePDFFile()
        tasks_pdf_file_path = []

        for task in task_objects:
            tasks_pdf_file_path.append(Rename.get_PDF_name(task.pdf_file_path))

        n_complete = bps.get_n_complete_tasks()
        n_total = len(task_objects)
        percent_complete = n_complete / n_total * 100

        zip_disabled = True
        status = 200
        if n_complete == n_total:
            status = 286
            zip_disabled = False

        context = {
            'tasks': zip(task_objects, tasks_pdf_file_path),
            'message': f'Progress: {n_complete} papers of {n_total} built ({percent_complete:.0f}%)',
            'zip_disabled': zip_disabled,
        }

        return render(request, 'BuildPaperPDF/fragments/pdf_table.html', context, status=status)


class GetPDFFile(View):
    # TODO: modify pdf file name
    def get(self, request, paper_number):
        pdf_file = PDFTask.objects.get(paper_number=paper_number).pdf_file_path
        pdf_path = pathlib.Path(pdf_file)
        if not pdf_path.exists() or not pdf_path.is_file():
            return HttpResponse(status=500)

        file = pdf_path.open('rb')
        pdf = SimpleUploadedFile('paper.pdf', file.read(), content_type='application/pdf')
        file.close()

        return FileResponse(pdf)


class GetCompressedPDFs(View):
    """Get the completed test paper PDFs in one zip file"""
    def post(self, request):
        bps = BuildPapersService()
        save_path = bps.get_pdf_zipfile()
        zip_file = save_path.open('rb')
        zf = SimpleUploadedFile(save_path.name, zip_file.read(), content_type='application/zip')
        zip_file.close()
        save_path.unlink()
        return FileResponse(zf)

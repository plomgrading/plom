import shutil
from django.http import FileResponse
from django.core.files.uploadedfile import SimpleUploadedFile
from Preparation.services import ExamMockerService, TestSourceService
from TestCreator.services import TestSpecService

from Preparation.views.needs_manager_view import ManagerRequiredBaseView

class MockExamView(ManagerRequiredBaseView):
    """Create a mock test PDF"""
    def post(self, request, version):
        mocker = ExamMockerService()
        tss = TestSourceService()
        spec = TestSpecService()
        source_path = tss.get_source_pdf_path(version)

        n_pages = spec.get_n_pages()
        pdf_path = mocker.mock_exam(version, source_path, n_pages, spec.get_short_name_slug())
        pdf_doc = SimpleUploadedFile(pdf_path.name, pdf_path.open('rb').read(), content_type='application/pdf')
        shutil.rmtree(pdf_path.parent)
        return FileResponse(pdf_doc)
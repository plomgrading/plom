from django.http import HttpResponse
from Preparation.services import ExamMockerService

from Preparation.views.needs_manager_view import ManagerRequiredBaseView

class MockExamView(ManagerRequiredBaseView):
    """Create a mock test PDF"""
    def post(self, request, version):
        mocker = ExamMockerService()
        mocked = mocker.mock_exam(version, 'lalalala')
        return HttpResponse(mocked)
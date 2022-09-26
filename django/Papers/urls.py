from django.urls import path
from Papers.views import CreateTestPapers, TestPaperProgress


urlpatterns = [
    path("init/", CreateTestPapers.as_view(), name="create_papers"),
    path("progress/", TestPaperProgress.as_view(), name="papers_progress"),
]

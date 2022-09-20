from django.urls import path
from Papers.views import CreateTestPapers


urlpatterns = [
    path("init/", CreateTestPapers.as_view(), name="create_papers"),
]
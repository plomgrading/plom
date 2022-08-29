from django.urls import path, include
from .views import (BuildPaperPDFs, GetPDFFile)

urlpatterns = [
    path("create/paperpdfs/", BuildPaperPDFs.as_view(), name="create_paperPDFs"),
    path("create/paperpdfs/get/<int:paper_number>", GetPDFFile.as_view(), name="get_paperPDFs"),
    # TODO: remeber to add <int: paper_number> back before get/
]

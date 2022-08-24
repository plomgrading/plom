from django.urls import path, include
from .views import (BuildTestPDFs, GetPDFFile)

urlpatterns = [
    path("create/testpdfs/", BuildTestPDFs.as_view(), name="create_testPDFs"),
    path("create/testpdfs/get/", GetPDFFile.as_view(), name="get_testPDFs"),
]

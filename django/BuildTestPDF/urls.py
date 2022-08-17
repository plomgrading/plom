from django.urls import path, include
from .views import (BuildTestPDFs)

urlpatterns = [
    path("create/testpdf/", BuildTestPDFs.as_view() , name="testPDF"),
]

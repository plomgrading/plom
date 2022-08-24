from django.urls import path, include
from .views import (BuildTestPDFs)

urlpatterns = [
    path("create/testpdfs/", BuildTestPDFs.as_view(), name="create_testPDFs"),
]

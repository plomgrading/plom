from datetime import datetime
from django.db import models

from Base.models import SingletonBaseModel, HueyTask


class CoreServerConnection(SingletonBaseModel):
    """Connect to core server"""
    server_name = models.TextField(default="")
    port_number = models.IntegerField(default=0)
    server_details = models.TextField(default="")
    client_version = models.TextField(default="0.10.0.dev")
    api_number = models.TextField(default="52")


class CoreManagerLogin(SingletonBaseModel):
    """Login details for the core manager account"""
    password = models.CharField(max_length=100)


class CoreScannerLogin(SingletonBaseModel):
    """Login details for the core scanner account"""
    scanner_username = models.CharField(max_length=100)
    scanner_password = models.CharField(max_length=100)


class CoreDBinitialiseTask(HueyTask):
    """Build the database in the background"""
    pass


class CoreDBRowTask(HueyTask):
    """Initialize a Core-DB row in the background"""
    paper_number = models.PositiveIntegerField(null=True)


class PreIDPapersTask(HueyTask):
    """Pre-ID papers in the background"""
    pass
from django.db import models

from Preparation.models import SingletonBaseModel


class CoreServerConnection(SingletonBaseModel):
    """Connect to core server"""
    server_url = models.TextField(default="")
    port_number = models.IntegerField(default=0)
    api = models.TextField(default="")
    client_version = models.TextField(default="")


class CoreManagerLogin(SingletonBaseModel):
    """Login details for the core manager account"""
    manager_username = models.CharField(max_length=100)
    manager_password = models.CharField(max_length=100)


class CoreScannerLogin(SingletonBaseModel):
    """Login details for the core scanner accont"""
    scanner_username = models.CharField(max_length=100)
    scanner_password = models.CharField(max_length=100)

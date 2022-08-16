from django.db import models

from Preparation.models import SingletonBaseModel


class CoreServerConnection(SingletonBaseModel):
    """Connect to core server"""
    server_url = models.TextField(default="localhost")
    port_number = models.IntegerField(default=41984)
    api = models.TextField(default="50")
    client_version = models.TextField(default="0.9.3.dev")


class CoreManagerLogin(SingletonBaseModel):
    """Login details for the core manager account"""
    manager_username = models.CharField(max_length=100)
    manager_password = models.CharField(max_length=100)


class CoreScannerLogin(SingletonBaseModel):
    """Login details for the core scanner accont"""
    scanner_username = models.CharField(max_length=100)
    scanner_password = models.CharField(max_length=100)

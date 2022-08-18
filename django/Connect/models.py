from django.db import models

from Preparation.models import SingletonBaseModel


class CoreServerConnection(SingletonBaseModel):
    """Connect to core server"""
    server_name = models.TextField(default="")
    port_number = models.IntegerField(default=0)
    server_details = models.TextField(default="")
    client_version = models.TextField(default="0.9.3.dev")
    api_number = models.TextField(default="50")


class CoreManagerLogin(SingletonBaseModel):
    """Login details for the core manager account"""
    password = models.CharField(max_length=100)


class CoreScannerLogin(SingletonBaseModel):
    """Login details for the core scanner accont"""
    scanner_username = models.CharField(max_length=100)
    scanner_password = models.CharField(max_length=100)

from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from model_bakery import baker
from .. import services


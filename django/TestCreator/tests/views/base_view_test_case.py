from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from model_bakery import baker


class BaseTestSpecViewTestCase(TestCase):
    """A base test case for the test spec views"""

    def setUp(self):
        """Create/force login a dummy manager user in order to access the view"""
        self.manager_user = baker.make("User")
        self.manager_group = baker.make("Group", name="manager")
        self.manager_user.groups.add(self.manager_group)

        self.cli = Client()
        self.cli.force_login(self.manager_user)
        return super().setUp()

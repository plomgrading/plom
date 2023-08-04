# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse

from model_bakery import baker
from ... import services

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.contrib import admin
from .models import StagingBundle, StagingImage, PageToImage

# Register your models here.
admin.site.register(StagingBundle)
admin.site.register(StagingImage)
admin.site.register(PageToImage)
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu

from django.contrib import admin
from .models import (
    StagingBundle,
    StagingImage,
    PageToImage,
    ParseQR,
    DiscardedStagingImage,
    CollisionStagingImage,
    UnknownStagingImage,
)

# Register your models here.
admin.site.register(StagingBundle)
admin.site.register(StagingImage)
admin.site.register(PageToImage)
admin.site.register(ParseQR)
admin.site.register(DiscardedStagingImage)
admin.site.register(CollisionStagingImage)
admin.site.register(UnknownStagingImage)

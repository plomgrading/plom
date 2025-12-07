# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023, 2025 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald

from django.contrib import admin

from .models import (
    StagingBundle,
    StagingImage,
    StagingThumbnail,
    PagesToImagesChore,
    ManageParseQRChore,
    KnownStagingImage,
    ExtraStagingImage,
    ErrorStagingImage,
)

# This makes models appear in the admin interface
admin.site.register(StagingBundle)
admin.site.register(StagingImage)
admin.site.register(StagingThumbnail)
admin.site.register(KnownStagingImage)
admin.site.register(ExtraStagingImage)
admin.site.register(ErrorStagingImage)
admin.site.register(PagesToImagesChore)
admin.site.register(ManageParseQRChore)

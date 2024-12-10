# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.contrib import admin

from .models import (
    StagingBundle,
    StagingImage,
    PagesToImagesHueyTask,
    ManageParseQR,
    ParseQR,
    KnownStagingImage,
    UnknownStagingImage,
    ExtraStagingImage,
    ErrorStagingImage,
    DiscardStagingImage,
)

# This makes models appear in the admin interface
admin.site.register(StagingBundle)
admin.site.register(StagingImage)
admin.site.register(KnownStagingImage)
admin.site.register(ExtraStagingImage)
admin.site.register(ErrorStagingImage)
admin.site.register(DiscardStagingImage)
admin.site.register(UnknownStagingImage)
admin.site.register(PagesToImagesHueyTask)
admin.site.register(ManageParseQR)
admin.site.register(ParseQR)

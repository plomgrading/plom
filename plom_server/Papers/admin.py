# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald

from django.contrib import admin

from .models.paper_structure import (
    Paper,
    MobilePage,
    FixedPage,
    IDPage,
    DNMPage,
    QuestionPage,
)
from .models.specifications import (
    NumberOfPapersToProduceSetting,
    SolnSpecification,
    SolnSpecQuestion,
    Specification,
    SpecQuestion,
)
from .models.background_tasks import CreateImageHueyTask, PopulateEvacuateDBChore
from .models.image_bundle import Image, DiscardPage, Bundle
from .models.reference_image import ReferenceImage

# This makes models appear in the admin interface
admin.site.register(NumberOfPapersToProduceSetting)
admin.site.register(Paper)
admin.site.register(SolnSpecification)
admin.site.register(SolnSpecQuestion)
admin.site.register(Specification)
admin.site.register(SpecQuestion)
admin.site.register(MobilePage)
admin.site.register(FixedPage)
admin.site.register(IDPage)
admin.site.register(DNMPage)
admin.site.register(QuestionPage)
admin.site.register(CreateImageHueyTask)
admin.site.register(PopulateEvacuateDBChore)
admin.site.register(Bundle)
admin.site.register(Image)
admin.site.register(DiscardPage)
admin.site.register(ReferenceImage)

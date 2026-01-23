# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023, 2025-2026 Colin B. Macdonald

"""Models of the Plom Server Paper app."""

from .image_bundle import (
    Bundle,
    Image,
    DiscardPage,
)

from .paper_structure import (
    Paper,
    FixedPage,
    MobilePage,
)
from .specifications import (
    SpecQuestion,
    Specification,
    SolnSpecification,
    SolnSpecQuestion,
)

# TODO: Issue #3140
from .background_tasks import CreateImageHueyTask, PopulateEvacuateDBChore

from .reference_image import ReferenceImage

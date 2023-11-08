# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from .image_bundle import (
    Bundle,
    Image,
    DiscardPage,
)

from .paper_structure import (
    Paper,
    FixedPage,
    DNMPage,
    IDPage,
    QuestionPage,
    MobilePage,
)
from .specifications import (
    SpecQuestion,
    Specification,
    SolutionSpecification,
)
from .background_tasks import CreatePaperHueyTask, CreateImageHueyTask

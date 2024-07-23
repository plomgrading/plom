# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Andrew Rechnitzer

from django.core.exceptions import ObjectDoesNotExist

from Preparation.services import (
    PapersPrinted,
    ScrapPaperService,
    ExtraPageService,
    StagingStudentService,
    PrenameSettingService,
    SourceService,
)
from BuildPaperPDF.services import BuildPapersService
from Papers.services import PaperCreatorService, SpecificationService


def reset_assessment_preparation_database():
    """Clean out any assessment preparation information from the database."""
    # Essentially the "Prepare assessment" page in reverse
    # Unset printed status
    PapersPrinted.set_papers_printed(False)

    # Remove Extra and Scrap Pages
    ScrapPaperService().delete_scrap_paper_pdf()
    ExtraPageService().delete_extra_page_pdf()

    # Remove all test PDFs
    BuildPapersService().reset_all_tasks()

    # Remove all test database rows
    PaperCreatorService.remove_all_papers_from_db(background=False)

    # Remove classlist
    StagingStudentService().remove_all_students()
    PrenameSettingService().set_prenaming_setting(False)

    # Remove and delete source PDFs
    SourceService.delete_all_source_pdfs()

    # Remove test spec
    try:
        SpecificationService.remove_spec()
    except ObjectDoesNotExist:
        pass

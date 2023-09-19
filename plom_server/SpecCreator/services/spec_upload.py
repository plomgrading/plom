# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path
from typing import Optional, Union, Dict, Any
from fitz import Document

from django.db import transaction

from Base.compat import load_toml_from_path, TOMLDecodeError

from Preparation.services import TestPreparedSetting, PQVMappingService

from Papers.services import SpecificationService, PaperInfoService
from Papers.serializers import SpecSerializer
from Papers.models import Specification

from . import ReferencePDFService, StagingSpecificationService


class SpecExistsException(Exception):
    """Raised if a specification already exists in the database."""


class SpecificationUploadService:
    """Handle the workflow of uploading a test specification from disk.

    The flow for uploading and saving a test spec:
        1. Manager has an already-existing TOML representing a test spec
            and one PDF representing a source version
        2. Manager requests to save the test spec from a path to a TOML
            file and another path to a reference PDF
        3. Server checks that a spec can be uploaded
            - Preparation must not be set as complete
            - There must be no existing QV map or test-papers
            - There must not be an existing spec
        4. If one of the first two is true, the server ends the workflow
            and tells the manager to remove the papers and/or QV map. If
            only the second is true, the client prompts the manager if they
            want to replace the spec.
            - If the manager agrees, the server deletes the current spec
            - Otherwise, the server ends the workflow.
        5. Server loads the toml and the reference PDF and validates them
            - TOML must be decoded and de-serialized into a Specification
                instance
            - Reference PDF must be readable by PyMuPDF and contain the
                same number of pages as the spec
        6. Server saves the Specification and updates the StagingSpecification
    """

    def __init__(
        self,
        *,
        toml_file_path: Union[str, Path, None] = None,
        reference_pdf_path: Union[str, Path, None] = None,
    ):
        """Construct service with paths and/or model instances.

        kwargs:
            toml_file_path: a path to a TOML specification
            reference_pdf_path: a path to a reference PDF
        """
        self.spec_dict: Optional[Dict[str, Any]] = None
        self.pdf_doc: Optional[Document] = None

        if toml_file_path:
            try:
                self.spec_dict = load_toml_from_path(toml_file_path)
            except TOMLDecodeError as e:
                raise ValueError("Unable to read TOML file.") from e

        if reference_pdf_path:
            try:
                self.pdf_doc = Document(reference_pdf_path)
            except Exception as e:
                raise ValueError("Unable to read reference PDF file.") from e

    @transaction.atomic
    def save_spec(
        self,
        *,
        update_staging: bool = False,
        custom_public_code: Optional[str] = None,
    ):
        """Save the specification to the database.

        kwargs:
            update_staging: whether to also update the StagingSpecification model.
            custom_public_code: override the randomly generated public code with a custom value.
        """
        if not self.spec_dict:
            raise ValueError("Cannot find specification to upload.")

        self.can_spec_be_modified(raise_exception=True)

        SpecificationService.load_spec_from_dict(
            self.spec_dict,
            update_staging=update_staging,
            public_code=custom_public_code,
        )

    @transaction.atomic
    def can_spec_be_modified(self, raise_exception: bool = False) -> bool:
        """Return true if the spec can be modified, false otherwise.

        To be able to modify (i.e. upload or replace) the test spec, these conditions must be met:
            - Test preparation must be set as "in progress"
            - There must be no existing test-papers
            - There must be no existing QV-map
            - There must not be an existing spec

        kwargs:
            raise_exception: if true, raise exceptions on assertion failure.
        """
        test_prepared = TestPreparedSetting.is_test_prepared()
        papers_created = PaperInfoService().is_paper_database_populated()
        qvmap_created = PQVMappingService().is_there_a_pqv_map()
        spec_exists = SpecificationService.is_there_a_spec()

        if raise_exception:
            if test_prepared:
                raise ValueError(
                    "Cannot modify spec while preparation is set as complete."
                )
            if papers_created:
                raise ValueError(
                    "Cannot save a new spec with test papers saved to the database."
                )
            if qvmap_created:
                raise ValueError(
                    "Cannot save a new spec while a question-version map exists."
                )

            if spec_exists:
                raise SpecExistsException("Specification already exists.")

        return not (test_prepared and papers_created and qvmap_created and spec_exists)

    @transaction.atomic
    def save_reference_pdf(self):
        """Save the reference PDF to the database."""
        if not self.pdf_doc:
            raise ValueError("Cannot find reference PDF to upload.")

        # TODO: assumes that a Specification (not staging) has been uploaded already
        if not SpecificationService.is_there_a_spec():
            raise RuntimeError("Spec has not been uploaded.")
        if self.pdf_doc.page_count != SpecificationService.get_n_pages():
            raise ValueError("Reference PDF does not match the spec's page count.")

        # TODO: refactor this part of the workflow into its own function-based services
        ref_service = ReferencePDFService()
        staging_service = StagingSpecificationService()
        ref_service.new_pdf(
            staging_service, "spec_reference.pdf", self.pdf_doc.page_count, self.pdf_doc
        )

    @transaction.atomic
    def delete_spec(self, *, delete_staging: bool = False):
        """Remove the specification from the database.

        kwargs:
            delete_staging: whether to remove the staging specification as well.
        """
        if not SpecificationService.is_there_a_spec():
            return

        self.can_spec_be_modified(raise_exception=True)

        SpecificationService.remove_spec()
        if delete_staging:
            StagingSpecificationService().reset_specification()

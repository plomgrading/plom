# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path
from typing import Optional, Union, Dict, Any
from fitz import Document

from django.db import transaction

from Base.compat import load_toml_from_path, load_toml_from_string, TOMLDecodeError

from Preparation.services import TestPreparedSetting, PQVMappingService

from Papers.services import SpecificationService, PaperInfoService
from Papers.serializers import SpecSerializer
from Papers.models import Specification


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
        5. Server loads and validates the toml
            - TOML must be decoded and de-serialized into a Specification
                instance
        6. Server saves the Specification
    """

    def __init__(
        self,
        *,
        toml_file_path: Union[str, Path, None] = None,
        toml_string: Optional[str] = None,
    ):
        """Construct service with paths and/or model instances.

        kwargs:
            toml_file_path: a path to a TOML specification
            toml_string: a raw string representing a TOML specification
            reference_pdf_path: a path to a reference PDF
        """
        self.spec_dict: Optional[Dict[str, Any]] = None
        self.pdf_doc: Optional[Document] = None

        if toml_file_path:
            try:
                self.spec_dict = load_toml_from_path(toml_file_path)
            except TOMLDecodeError as e:
                raise ValueError("Unable to read TOML file.") from e
        elif toml_string:
            try:
                self.spec_dict = load_toml_from_string(toml_string)
            except TOMLDecodeError as e:
                raise ValueError("Unable to parse TOML file from string.") from e

    @transaction.atomic
    def save_spec(
        self,
        *,
        custom_public_code: Optional[str] = None,
    ):
        """Save the specification to the database.

        kwargs:
            custom_public_code: override the randomly generated public code with a custom value.
        """
        if not self.spec_dict:
            raise ValueError("Cannot find specification to upload.")

        self.can_spec_be_modified(raise_exception=True)

        SpecificationService.load_spec_from_dict(
            self.spec_dict,
            public_code=custom_public_code,
        )

    @transaction.atomic
    def can_spec_be_modified(self, raise_exception: bool = False) -> bool:
        """Return true if the spec can be modified, false otherwise.

        To be able to modify (i.e. upload or replace) the test spec, these conditions must be met:
            - Test preparation must be set as "in progress"
            - There must be no existing test-papers
            - There must be no existing QV-map

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

        return not (test_prepared and papers_created and qvmap_created and spec_exists)

    @transaction.atomic
    def delete_spec(self, *args):
        """Remove the specification from the database."""
        if not SpecificationService.is_there_a_spec():
            return
        SpecificationService.remove_spec()

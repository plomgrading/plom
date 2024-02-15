# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer

from pathlib import Path
from typing import Optional, Union, Dict, Any

from django.db import transaction

from Base.compat import load_toml_from_path, load_toml_from_string, TOMLDecodeError

from Preparation.services import PapersPrinted, PQVMappingService

from Papers.services import SpecificationService, PaperInfoService


class SpecExistsException(Exception):
    """Raised if a specification already exists in the database."""


class SpecificationUploadService:
    """Handle the workflow of uploading a test specification from disk.

    The flow for uploading and saving a test spec:
        1. Manager has an already-existing TOML representing a test spec
        2. Manager requests to save the test spec from a path to a TOML
            file.
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

        Note: If the service is initialized with both a toml file path
        and a toml string, it will read and use the toml file and ignore
        the string.

        Keyword Args::
            toml_file_path: a path to a TOML specification.  Callers
                must provide either this input or the ``toml_string``.
            toml_string: a raw string representing a TOML specification

        Raises:
            ValueError on failure to parse the TOML.
        """
        self.spec_dict: Optional[Dict[str, Any]] = None

        if toml_file_path:
            try:
                self.spec_dict = load_toml_from_path(toml_file_path)
            except TOMLDecodeError as e:
                raise ValueError(f"Unable to read TOML file: {e}") from e
        elif toml_string:
            try:
                self.spec_dict = load_toml_from_string(toml_string)
            except TOMLDecodeError as e:
                raise ValueError(f"Unable to parse TOML: {e}") from e

    def validate_spec(self):
        SpecificationService.validate_spec_from_dict(
            self.spec_dict,
        )

    @transaction.atomic
    def save_spec(
        self,
        *,
        custom_public_code: Optional[str] = None,
    ):
        """Save the specification to the database if possible.

        Keyword Args:
            custom_public_code: override the randomly generated public code with a custom value.

        Raises:
            ValueError: various reasons for not being able to change
                the spec.
        """
        if not self.spec_dict:
            raise ValueError("Cannot find specification to upload.")

        self.can_spec_be_modified(raise_exception=True)

        SpecificationService.load_spec_from_dict(
            self.spec_dict,
            public_code=custom_public_code,
        )

    @transaction.atomic
    def can_spec_be_modified(self, *, raise_exception: bool = False) -> bool:
        """Return true if the spec can be modified, false otherwise.

        To be able to modify (i.e. upload or replace) the test spec, these conditions must be met:
            - Test preparation must be set as "in progress"
            - There must be no existing test-papers
            - There must be no existing QV-map

        Keyword Args:
            raise_exception: if true, raise exceptions on assertion failure.
        """
        papers_printed = PapersPrinted.have_papers_been_printed()
        papers_created = PaperInfoService().is_paper_database_populated()
        qvmap_created = PQVMappingService().is_there_a_pqv_map()

        if papers_printed:
            if raise_exception:
                raise ValueError("Cannot modify spec once papers have been printed.")
            return False

        if papers_created:
            if raise_exception:
                raise ValueError(
                    "Cannot save a new spec with test papers saved to the database."
                )
            return False

        if qvmap_created:
            if raise_exception:
                raise ValueError(
                    "Cannot save a new spec while a question-version map exists."
                )
            return False

        return True

    @transaction.atomic
    def delete_spec(self):
        """Remove the specification from the database.

        Raises:
            ValueError: various reasons for not being able to change
                the spec.
        """
        if not SpecificationService.is_there_a_spec():
            return
        self.can_spec_be_modified(raise_exception=True)
        SpecificationService.remove_spec()

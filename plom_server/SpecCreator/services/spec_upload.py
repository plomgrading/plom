# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2025 Philip D. Loewen

from pathlib import Path
from typing import Any

from django.db import transaction

from plom_server.Base.compat import (
    load_toml_from_path,
    load_toml_from_string,
    TOMLDecodeError,
)

from plom_server.Preparation.services.preparation_dependency_service import (
    assert_can_modify_spec,
)

from plom_server.Papers.services import SpecificationService


class SpecificationUploadService:
    """Handle the workflow of uploading a assessment specification.

    The flow for uploading and saving a spec:
        1. Manager has an already-existing TOML representing a spec
        2. Manager requests to save the spec from a path to a TOML
            file.
        3. Server checks that a spec can be uploaded
            - Preparation must not be set as complete
            - There must be no existing QV map or papers
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
        toml_file_path: str | Path | None = None,
        toml_string: str | None = None,
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
        self.spec_dict: dict[str, Any] = {}

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

    def _validate_spec(self) -> None:
        """A frontend to a some serializer stuff.

        Perhaps callers should use the Serializer directly instead of this,
        hence the underscore.

        Raises:
            ValueError: no spec to validate
            serializers.ValidationError: the ``.detail`` field will contain
                a list of what is wrong.
        """
        if not self.spec_dict:
            raise ValueError("Cannot find specification to validate.")
        # Note this returns bool and we ignore it
        SpecificationService.validate_spec_from_dict(self.spec_dict)

    @transaction.atomic
    def save_spec(
        self,
        *,
        custom_public_code: str | None = None,
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

        assert_can_modify_spec()

        SpecificationService.load_spec_from_dict(
            self.spec_dict,
            public_code=custom_public_code,
        )

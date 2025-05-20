# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

"""Handle creating pre-bundle server state from a config file.

Assumes that the config describes a valid server state, and that the
server will be created in order from test specification to building test-papers.
"""

import sys
from importlib import resources

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from plom_server.Papers.services import PaperCreatorService, SpecificationService
from plom_server.Preparation import useful_files_for_testing as useful_files
from plom_server.Preparation.services import (
    PapersPrinted,
    PQVMappingService,
    PrenameSettingService,
    SourceService,
    StagingStudentService,
)

from . import PlomConfigCreationError, PlomServerConfig


def list_files_recursively(path):
    print("+" * 20)
    for item in path.iterdir():
        if item.is_file():
            print(f"File: {item}")
        elif item.is_dir():
            print(f"Directory: {item}")
            list_files_recursively(item)
    print("+" * 20)


def create_specification(config: PlomServerConfig):
    """Create a test specification from a config."""
    spec_path = config.test_spec
    if spec_path is None:
        return

    try:
        if spec_path == "demo":
            list_files_recursively(resources.files(useful_files))
            spec_src = resources.files(useful_files) / "testing_test_spec.toml"
        else:
            spec_src = config.parent_dir / spec_path
        # mypy stumbling over Traverseable?
        SpecificationService.install_spec_from_toml_file(spec_src)  # type: ignore[arg-type]
    except Exception as e:
        raise PlomConfigCreationError(e) from e


def upload_test_sources(config: PlomServerConfig) -> None:
    """Upload test sources specified in a config."""
    source_paths = config.test_sources
    if source_paths == "demo":
        list_files_recursively(resources.files(useful_files))
        version1 = resources.files(useful_files) / "test_version1.pdf"
        version2 = resources.files(useful_files) / "test_version2.pdf"
        # mypy stumbling over Traverseable?  but abc.Traversable added in Python 3.11
        source_paths = [version1, version2]  # type: ignore[list-item]

    try:
        assert isinstance(source_paths, list)
        for i, path in enumerate(source_paths):
            SourceService.store_source_pdf(i + 1, path)
    except Exception as e:
        raise PlomConfigCreationError(e) from e


def set_prenaming_setting(config: PlomServerConfig):
    """Set prenaming according to a config."""
    PrenameSettingService().set_prenaming_setting(config.prenaming_enabled)


def upload_classlist(config: PlomServerConfig):
    """Upload classlist specified in a config."""
    classlist_path = config.classlist
    if classlist_path == "demo":
        list_files_recursively(resources.files(useful_files))
        # mypy stumbling over Traverseable?  but abc.Traversable added in Python 3.11
        classlist_path = resources.files(useful_files) / "cl_for_demo.csv"  # type: ignore[assignment]

    assert classlist_path is not None
    assert not isinstance(classlist_path, str)
    try:
        with classlist_path.open("rb") as classlist_f:
            sss = StagingStudentService()
            success, warnings = sss.validate_and_use_classlist_csv(
                classlist_f, ignore_warnings=True
            )
        if not success:
            raise PlomConfigCreationError("Unable to upload classlist.")
    except Exception as e:
        raise PlomConfigCreationError(e) from e


def create_qv_map_and_papers(config: PlomServerConfig):
    """Create a QVmap from a config and use it to populate the paper database.

    Either generated from a number-to-produce value or a link to a QVmap CSV.
    """
    qvmap: dict[int, dict[int | str, int]] = {}
    if config.num_to_produce:
        qvmap = PQVMappingService().make_version_map(config.num_to_produce)
    else:
        # TODO: extra validation steps here?
        try:
            qvmap_path = config.qvmap
            if qvmap_path is None:
                raise RuntimeError(
                    "Number to produce and qvmap path missing from config."
                )

            # Some duplicated code here from `plom.version_maps``
            qvmap_path = config.parent_dir / qvmap_path
            with open(qvmap_path, "rb") as qvmap_file:
                qvmap_rows = tomllib.load(qvmap_file)
                for i in range(len(qvmap_rows)):
                    paper_number = i + 1
                    row = qvmap_rows[str(paper_number)]
                    qvmap[paper_number] = {
                        j: row[j - 1] for j in range(1, len(row) + 1)
                    }
        except Exception as e:
            raise PlomConfigCreationError(e) from e
    try:
        PaperCreatorService.add_all_papers_in_qv_map(qvmap, _testing=True)
    except Exception as e:
        raise PlomConfigCreationError(e) from e


def create_test_preparation(config: PlomServerConfig, verbose: bool = False):
    """Instantiate models from the test specification to test-papers."""

    def echo(x):
        return print(x) if verbose else None

    echo("Creating specification...")
    create_specification(config)

    if config.test_sources:
        echo("Uploading test sources...")
        upload_test_sources(config)

    echo("Setting prenaming and uploading classlist...")
    if config.prenaming_enabled:
        set_prenaming_setting(config)
    if config.classlist:
        upload_classlist(config)

    if config.num_to_produce or config.qvmap:
        echo("Creating question-version map and populating database...")
        create_qv_map_and_papers(config)

    # here we override the dependency checking since
    # we do not want to actually build pdfs.
    PapersPrinted.set_papers_printed(True, ignore_dependencies=True)
    echo("Preparation complete, papers printed.")

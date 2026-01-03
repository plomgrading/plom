# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024-2026 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

from plom.plom_exceptions import PlomDependencyConflict

# move all service imports into the functions in order
# to avoid circular-dependency hell

# preparation steps are
# 1 = spec
# 2 = source pdfs
# 3 = classlist and prenaming
# 4 = qv-mapping and db-populate
# 5 = build paper pdfs
# 6 = tell plom papers are printed.

# give assert raising tests followed by true/false returning functions


# 1 = the spec depends on nothing, but sources and QVMap depend on the spec
def assert_can_modify_spec():
    from plom_server.Papers.services import PaperInfoService
    from . import PapersPrinted, SourceService

    # cannot modify spec if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict(
            "Cannot modify spec because papers have been printed."
        )
    # if any sources uploaded, then cannot modify spec.
    if SourceService.how_many_source_versions_uploaded() > 0:
        raise PlomDependencyConflict(
            "Cannot modify spec because source PDFs "
            "for your assessment have been uploaded."
        )
    # cannot modify spec if there is a QVmap (e.g., change number of questions)
    # TODO: in theory, we could allow finer-grained edits, such as points.
    if PaperInfoService.is_paper_database_populated():
        raise PlomDependencyConflict(
            "Cannot save a new spec while there is an existing "
            "paper-question-version map: try deleting that first."
        )


# 2 = the sources depend on the spec, and built-papers depend on the sources
def assert_can_modify_sources(*, deleting: bool = False) -> None:
    from . import PapersPrinted
    from plom_server.Papers.services import SpecificationService
    from plom_server.BuildPaperPDF.services import BuildPapersService

    # cannot modify sources if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # if there is no spec, then cannot modify sources (unless deleting)
    if not deleting:
        if not SpecificationService.is_there_a_spec():
            raise PlomDependencyConflict("There is no specification.")
    # cannot modify sources if any papers have been produced
    if BuildPapersService().are_any_papers_built():
        raise PlomDependencyConflict(
            "Paper PDFs have been built - these depend on the source PDFs."
        )


# 3 = classlist and prenaming.
# 3a = classlist - does not depend on spec, but the database depends on prenaming and classlist.
def assert_can_modify_classlist():
    from . import PapersPrinted, StagingStudentService
    from plom_server.Papers.services import PaperInfoService

    # Issue = #3635
    # if papers have been printed you are allowed to modify
    # the classlist.
    if PapersPrinted.have_papers_been_printed():
        return
    # if db populated (or being populated) and classlist includes prenames, then cannot modify classlist
    if StagingStudentService.are_there_any_prenamed_papers():
        if PaperInfoService.is_paper_database_populated():
            raise PlomDependencyConflict(
                "Database has been populated with some prenamed papers,"
                " so the classlist cannot be changed."
            )
        if PaperInfoService.is_paper_database_being_updated_in_background():
            raise PlomDependencyConflict(
                "Database is now being updated with some prenamed papers,"
                " so the classlist cannot be changed."
            )


def assert_can_modify_prenaming_config():
    """Raises an error if the server state doesn't permit modifying prenaming config.

    Returns:
        None

    Raises:
        PlomDependencyConflict
    """
    from . import PapersPrinted, SourceService
    from plom_server.Papers.services import SpecificationService
    from plom_server.BuildPaperPDF.services import BuildPapersService

    # cannot configure prenaming if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")

    # cannot configure prenaming if papers built
    if BuildPapersService().are_any_papers_built():
        raise PlomDependencyConflict("Paper PDFs have been built.")

    # cannot configure prenaming without version 1 source PDF
    # (Note Issue #3390: ID pages can have other versions but I think this restriction
    # is (mostly?) about drawing the UI, which currently uses only version 1.)
    if not SourceService.get_source(1)["uploaded"]:
        raise PlomDependencyConflict(
            "Source PDF for assessment version 1 has not been uploaded."
        )

    # cannot configure prenaming if ID page is unknown
    if not SpecificationService.is_there_a_spec():
        raise PlomDependencyConflict("There is no specification.")


# 4 - qvmap depends on the spec, build papers depends on the qvmap
def assert_can_modify_qv_mapping_database(*, deleting: bool = False) -> None:
    from . import PapersPrinted
    from plom_server.Papers.services import SpecificationService
    from plom_server.BuildPaperPDF.services import BuildPapersService

    # cannot modify qv mapping / database if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # cannot modify the qv-mapping if there is no spec (but deleting ok)
    if not deleting:
        if not SpecificationService.is_there_a_spec():
            raise PlomDependencyConflict("There is no assessment spec.")

    # cannot modify qv-mapping if papers have been produced
    if BuildPapersService().are_any_papers_built():
        raise PlomDependencyConflict("Paper PDFs have been built.")


# 5 - the paper pdfs depend on the qv-map/db and source pdfs. Nothing depends on the paper-pdfs
def assert_can_rebuild_test_pdfs():
    from . import PapersPrinted, SourceService
    from plom_server.Papers.services import PaperInfoService

    # cannot rebuild paper pdfs if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # and we need sources-pdfs and a populated db
    if not SourceService.are_all_sources_uploaded():
        raise PlomDependencyConflict("Some source PDFs have not been uploaded.")
    if not PaperInfoService.is_paper_database_populated():
        raise PlomDependencyConflict(
            "The database does not contain a complete set of paper definitions."
        )
    if PaperInfoService.is_paper_database_being_updated_in_background():
        raise PlomDependencyConflict("The database is being updated.")


# now the true/false versions of these functions
# assert_can_modify_spec
def can_modify_spec():
    try:
        assert_can_modify_spec()
        return True
    except PlomDependencyConflict:
        return False


# assert_can_modify_sources
def can_modify_sources():
    try:
        assert_can_modify_sources()
        return True
    except PlomDependencyConflict:
        return False


# assert_can_modify_classlist
def can_modify_classlist():
    try:
        assert_can_modify_classlist()
        return True
    except PlomDependencyConflict:
        return False


def can_modify_prenaming_config():
    """Checks if server state permits modification of prenaming config.

    Returns:
        bool: True if changes are permitted, False if not.
    """
    try:
        assert_can_modify_prenaming_config()
        return True
    except PlomDependencyConflict:
        return False


# assert_can_modify_qv_mapping_database
def can_modify_qv_mapping_database():
    try:
        assert_can_modify_qv_mapping_database()
        return True
    except PlomDependencyConflict:
        return False


# assert_can_rebuild_test_pdfs
def can_rebuild_test_pdfs():
    try:
        assert_can_rebuild_test_pdfs()
        return True
    except PlomDependencyConflict:
        return False


def assert_can_set_papers_printed():
    # can set papers_printed once all PDFs are built.
    from plom_server.BuildPaperPDF.services import BuildPapersService

    if not BuildPapersService().are_all_papers_built():
        raise PlomDependencyConflict(
            "Cannot set papers-printed since not all paper-pdfs have been built."
        )


def assert_can_unset_papers_printed():
    # can unset papers_printed provided no bundles have neen scanned.
    from plom_server.Papers.models import Bundle
    from plom_server.Scan.models import StagingBundle

    # if any bundles uploaded then raise an exception
    # remember to exclude system bundles
    if (
        StagingBundle.objects.exists()
        or Bundle.objects.filter(_is_system=False).exists()
    ):
        raise PlomDependencyConflict(
            "Cannot unset papers-printed because bundles have been uploaded."
        )


def can_set_papers_printed():
    try:
        assert_can_set_papers_printed()
        return True
    except PlomDependencyConflict:
        return False


def can_unset_papers_printed():
    try:
        assert_can_unset_papers_printed()
        return True
    except PlomDependencyConflict:
        return False

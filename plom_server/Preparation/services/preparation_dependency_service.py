# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from plom.plom_exceptions import PlomDependencyConflict

from BuildPaperPDF.services import BuildPapersService
from . import SourceService, PapersPrinted, PrenameSettingService, StagingStudentService

from Papers.services import (
    SpecificationService,
    PaperInfoService,
)

# preparation steps are
# 1 = test-spec
# 2 = source pdfs
# 3 = classlist and prenaming
# 4 = qv-mapping and db-populate
# 5 = build tests paper pdfs
# 6 = tell plom papers are printed.


# 1 the test spec depends on nothing, but
# sources depend on the spec
def can_modify_spec() -> bool:
    # cannot modify spec if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # if any sources uploaded, then cannot modify spec.
    if SourceService.how_many_source_versions_uploaded() > 0:
        raise PlomDependencyConflict(
            "Source PDFs for your assessment have been uploaded."
        )
    # TODO - decide if spec can be changed with/without classlist
    return True


# 2 = the sources depend on the spec,
# and built-papers depend on the sources
def can_modify_sources() -> bool:
    # cannot modify sources if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # if there is no spec, then cannot modify sources
    if not SpecificationService.is_there_a_spec():
        raise PlomDependencyConflict("There is no test specification")
    # cannot modify sources if any papers have been produced
    if BuildPapersService().are_any_papers_built():
        raise PlomDependencyConflict("Test PDFs have been built.")
    return True


# 3 = classlist and prenaming - does not depend on spec, but
# the database depends on prenaming and classlist.
def can_modify_classlist_and_prenaming() -> bool:
    # cannot modify prenaming if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # TODO - decide if this should depend on presence of spec.
    # if not SpecificationService.is_there_a_spec():
    #     raise PlomDependencyConflict("There is no test specification")
    # if the qv-mapping/database is built then cannot modify classlist/prenaming.
    if not PaperInfoService().is_paper_database_populated():
        raise PlomDependencyConflict(
            "The qv-mapping has been built and the database have been populated."
        )
    return True


# 4 - the qv-mapping depends on the classlist (prenaming), spec.
# and the built papers depend on the qv-mapping.
def can_modify_qv_mapping_database() -> bool:
    # cannot modify qv mapping / database if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # cannot modify the qv-mapping if there is no spec
    if not SpecificationService.is_there_a_spec():
        raise PlomDependencyConflict("There is no test specification")

    # if prenaming set, then we must have a classlist before can modify qv-map.
    # else we can modify independent of the classlist.
    if PrenameSettingService.get_prenaming_setting():
        if not StagingStudentService().are_there_students():
            raise PlomDependencyConflict(
                "Prenaming enabled, but no classlist has been uploaded"
            )
        else:  # have classlist and prenaming set, so can modify qv-map
            pass
    else:  # prenaming not set, so can modify qv-map indep of classlist.
        pass

    # cannot modify qv-mapping if test papers have been produced
    if BuildPapersService().are_any_papers_built():
        raise PlomDependencyConflict("Test PDFs have been built.")
    return True


# 5 - the test pdfs depend on the qv-map/db and source pdfs.
# nothing depends on the test-pdfs
def can_rebuild_test_pdfs() -> bool:
    # cannot rebuild test pdfs if papers printed
    if PapersPrinted.have_papers_been_printed():
        raise PlomDependencyConflict("Papers have been printed.")
    # and we need sources-pdfs and a populated db
    if not SourceService.are_all_sources_uploaded():
        raise PlomDependencyConflict("Not all source PDFs have been uploaded.")
    if not PaperInfoService().is_paper_database_populated():
        raise PlomDependencyConflict(
            "The qv-mapping has been built and the database have been populated."
        )
    return True

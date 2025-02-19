# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from django.core.management.base import BaseCommand, CommandError

from Papers.services import PaperInfoService, SpecificationService
from ...services import (
    SourceService,
    PrenameSettingService,
    PapersPrinted,
)
from ...services.preparation_dependency_service import (
    can_set_papers_printed,
    can_unset_papers_printed,
)


class Command(BaseCommand):
    help = "Get the status of assessment prepartaion, and mark preparation as either finished or in progress."

    def add_arguments(self, parser):
        grp = parser.add_mutually_exclusive_group(required=True)
        grp.add_argument(
            "--get",
            action="store_true",
            help="Get the current status of preparation.",
        )
        grp.add_argument(
            "--set",
            action="store",
            nargs=1,
            choices=["finished", "todo"],
            help="Set preparation status and enable/disable bundle uploading.",
        )

    def handle(self, *args, **options):
        if options["get"]:
            spec_status = SpecificationService.is_there_a_spec()
            self.stdout.write(f"Specification present: {spec_status}")

            sources_total = SpecificationService.get_n_versions()
            num_sources_present = SourceService.how_many_source_versions_uploaded()
            self.stdout.write(
                f"{num_sources_present} of {sources_total} PDF source(s) present"
            )

            prename_status = PrenameSettingService().get_prenaming_setting()
            self.stdout.write(f"Prenaming enabled: {prename_status}")

            papers_status = PaperInfoService.is_paper_database_populated()
            self.stdout.write(f"Paper QV map saved to database: {papers_status}")

            prep_setting = PapersPrinted.have_papers_been_printed()
            prep_status = "finished" if prep_setting else "todo"
            self.stdout.write(f"Paper-printing set as: {prep_status}")
        else:
            status = options["set"][0]
            if status == "finished":
                if not can_set_papers_printed():
                    raise CommandError(
                        "Unable to set paper-printing as finished - "
                        "papers have not been saved to the database."
                    )
                PapersPrinted.set_papers_printed(True)
            elif status == "todo":
                if not can_unset_papers_printed():
                    raise CommandError(
                        "Unable to set paper-printing as todo - "
                        "bundles have been pushed to the database."
                    )
                PapersPrinted.set_papers_printed(False)
            else:
                return

            self.stdout.write(f"Preparation set as {status}.")

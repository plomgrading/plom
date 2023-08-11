# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.core.management.base import BaseCommand, CommandError

from Papers.services import PaperInfoService, SpecificationService
from Progress.services import ManageScanService
from ...services import (
    TestSourceService,
    PrenameSettingService,
    StagingStudentService,
    PQVMappingService,
    TestPreparedSetting,
)


class Command(BaseCommand):
    help = "Get the status of test prepartaion, and mark preparation as either finished or in progress."

    def add_arguments(self, parser):
        grp = parser.add_mutually_exclusive_group(required=True)
        grp.add_argument(
            "--get",
            action="store_true",
            help="Get the current status of test preparation.",
        )
        grp.add_argument(
            "--set",
            action="store",
            nargs=1,
            choices=["finished", "todo"],
            help="Set preparation status and enable/disable bundle uploading.",
        )

    def can_status_be_set_true(self):
        return PaperInfoService().is_paper_database_populated()

    def can_status_be_set_false(self):
        return ManageScanService().get_number_pushed_bundles() == 0

    def handle(self, *args, **options):
        if options["get"]:
            spec_status = SpecificationService.is_there_a_spec()
            self.stdout.write(f"Test specification present: {spec_status}")

            sources_total = SpecificationService.get_n_versions()
            sources_present = TestSourceService().how_many_test_versions_uploaded()
            self.stdout.write(
                f"{sources_present} of {sources_total} test source(s) present"
            )

            prename_status = PrenameSettingService().get_prenaming_setting()
            self.stdout.write(f"Prenaming enabled: {prename_status}")

            qvmap_status = PQVMappingService().is_there_a_pqv_map()
            self.stdout.write(f"Question-version map present: {qvmap_status}")

            papers_status = PaperInfoService().is_paper_database_populated()
            self.stdout.write(f"Test papers saved to database: {papers_status}")

            prep_setting = TestPreparedSetting.is_test_prepared()
            prep_status = "finished" if prep_setting else "todo"
            self.stdout.write(f"Preparation set as: {prep_status}")
        else:
            status = options["set"][0]
            if status == "finished":
                if not self.can_status_be_set_true():
                    raise CommandError(
                        "Unable to mark status as finished - test-papers have not been saved to the database."
                    )
                TestPreparedSetting.set_test_prepared(True)
            elif status == "todo":
                if not self.can_status_be_set_false():
                    raise CommandError(
                        "Unable to mark status as todo - bundles have been pushed to the database."
                    )
                TestPreparedSetting.set_test_prepared(False)
            else:
                return

            self.stdout.write(f"Preparation set as {status}.")

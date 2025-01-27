# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald

from importlib import resources

from django.core.management.base import BaseCommand, CommandError

from Papers.services import SpecificationService
from Preparation import useful_files_for_testing as useful_files


class Command(BaseCommand):
    """Push simple demo data to the test specification creator app.

    Also, can clear the current test specification.
    """

    help = "Create a demo test specification."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear an existing test specification.",
        )
        parser.add_argument(
            "--publicCode",
            type=int,
            help="Force the spec to use a pre-determined public code.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            if SpecificationService.is_there_a_spec():
                SpecificationService.remove_spec()
                self.stdout.write("Test specification cleared.")
            else:
                self.stdout.write("No specification uploaded.")
        else:
            if SpecificationService.is_there_a_spec():
                self.stderr.write(
                    "Test specification data already present. Run manage.py plom_demo_spec --clear to clear the current specification."
                )
            else:
                self.stdout.write("Writing test specification...")

                # verify spec, stage + save to DB
                try:
                    demo_toml_path = (
                        resources.files(useful_files) / "testing_test_spec.toml"
                    )

                    if options["publicCode"]:
                        code = options["publicCode"]
                    else:
                        code = None

                    SpecificationService.load_spec_from_toml(
                        pathname=demo_toml_path,
                        public_code=code,
                    )

                    self.stdout.write("Demo test specification uploaded!")
                    self.stdout.write(str(SpecificationService.get_the_spec()))
                except ValueError as e:
                    raise CommandError(e)

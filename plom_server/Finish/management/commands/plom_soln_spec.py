# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

import sys
from pathlib import Path

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from rest_framework.serializers import ValidationError

from Papers.services import SolnSpecService
from ...services import TemplateSolnSpecService


class Command(BaseCommand):
    """Create draft, upload, download, remove a solution specification."""

    def show_status(self):
        if SolnSpecService.is_there_a_soln_spec():
            self.stdout.write("There is a solution specification")
            unused_pages = SolnSpecService.get_unused_pages()
            numberOfPages = SolnSpecService.get_n_pages()
            self.stdout.write(
                f"Note that the soln spec contains {numberOfPages} pages of which {unused_pages} are unused."
            )
        else:
            self.stdout.write("There is no solution specification")

    def create_template_spec(self, destination: str):
        soln_spec_toml = TemplateSolnSpecService().build_template_soln_toml()

        dest_path = Path(destination)
        if dest_path.exists():
            self.stderr.write(f"File {dest_path} already exists")
            return
        with dest_path.open("w") as fh:
            fh.write(soln_spec_toml)
        self.stdout.write(f"Wrote draft solution spec to {dest_path}")

    def upload_spec(self, soln_spec_file: str):
        if SolnSpecService.is_there_a_soln_spec():
            raise CommandError("The server already has a solution specification")

        spec_path = Path(soln_spec_file)
        if spec_path.exists() is False:
            raise CommandError(f"Cannot open {spec_path}.")

        try:
            with open(spec_path, "rb") as fh:
                spec_dict = tomllib.load(fh)
        except tomllib.TOMLDecodeError as err:
            raise CommandError(err)
        self.stdout.write(f"From {spec_path} read spec dict = {spec_dict}")

        try:
            SolnSpecService.load_soln_spec_from_dict(spec_dict)
        except ValueError as err:
            raise CommandError(err)
        except ValidationError as err:
            raise CommandError(err)

        unused_pages = SolnSpecService.get_unused_pages()
        numberOfPages = SolnSpecService.get_n_pages()
        self.stdout.write("Solution spec uploaded.")
        self.stdout.write(
            f"Note that the soln spec contains {numberOfPages} pages of which {unused_pages} are unused."
        )

    def remove_spec(self):
        try:
            SolnSpecService.remove_soln_spec()
        except ObjectDoesNotExist as err:
            raise CommandError(err)

    def download_spec(self, destination: str):
        if not SolnSpecService.is_there_a_soln_spec():
            self.stdout.write("There is no solution specification")
        soln_spec_toml = SolnSpecService.get_the_soln_spec_as_toml()

        dest_path = Path(destination)
        if dest_path.exists():
            self.stderr.write(f"File {dest_path} already exists")
            return
        with dest_path.open("w") as fh:
            fh.write(soln_spec_toml)
        self.stdout.write(f"Wrote solution spec to {dest_path}")

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Perform tasks related to uploading/downloading/deleting of a solution specification.",
        )
        sub.add_parser("status", help="Show details of current solution spec")
        sp_C = sub.add_parser(
            "create",
            help="Create a template solution spec from the test spec and (by default) save as 'draft_soln_spec.toml'",
        )
        sp_U = sub.add_parser("upload", help="Upload a solution spec")
        sp_D = sub.add_parser(
            "download", help="Download the current solution spec (if is valid)"
        )

        sp_U.add_argument(
            "soln_spec_toml", type=str, help="The solution spec toml to upload"
        )

        sp_C.add_argument(
            "dest",
            type=str,
            nargs="?",
            help="Where to download the draft solution spec toml",
            default="draft_soln_spec.toml",
        )
        sp_D.add_argument(
            "dest",
            type=str,
            nargs="?",
            help="Where to download the solution spec toml",
            default="soln_spec.toml",
        )
        sub.add_parser(
            "remove", help="Remove the current solution spec from the server"
        )

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_status()
        elif options["command"] == "create":
            self.create_template_spec(options["dest"])
        elif options["command"] == "upload":
            self.upload_spec(options["soln_spec_toml"])
        elif options["command"] == "remove":
            self.remove_spec()
        elif options["command"] == "download":
            self.download_spec(options["dest"])
        else:
            self.print_help("manage.py", "plom_solution_spec")

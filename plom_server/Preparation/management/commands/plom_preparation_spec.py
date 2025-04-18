# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023, 2025 Colin B. Macdonald

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.text import slugify

from plom_server.Papers.services import SpecificationService
from plom_server.SpecCreator.services import SpecificationUploadService


class Command(BaseCommand):
    help = "Displays the current status of the spec, and allows user to upload/download/remove."

    def show_status(self) -> None:
        if not SpecificationService.is_there_a_spec():
            self.stdout.write("No assessment specification present")
            return

        toml_text = SpecificationService.get_the_spec_as_toml()
        self.stdout.write("A valid assessment specification is present:")
        self.stdout.write("#" * 40)
        self.stdout.write(f"{toml_text}")
        self.stdout.write("#" * 40)

    def download_spec(self, dest: str | Path | None = None) -> None:
        if not SpecificationService.is_there_a_spec():
            raise CommandError("No specification is present")

        spec_dict = SpecificationService.get_the_spec()
        self.stdout.write(
            f"A valid assessment spec is present: shortname {spec_dict['name']}"
        )
        if dest is None:
            fname = Path(slugify(spec_dict["name"]) + "_spec.toml")
        else:
            fname = Path(dest)
        self.stdout.write(f"Writing assessment specification to {fname}")
        if fname.exists():
            raise CommandError(f"File {fname} already present - not overwriting.")
        with open(fname, "w") as f:
            f.write(SpecificationService.get_the_spec_as_toml())

    def upload_spec(self, spec_file: str | Path) -> None:
        try:
            service = SpecificationUploadService(toml_file_path=spec_file)
            service.save_spec()
        except ValueError as e:
            raise CommandError(e) from e

        self.stdout.write("Assessment specification uploaded to server.")

    def remove_spec(self) -> None:
        if not SpecificationService.is_there_a_spec():
            raise CommandError("No specification uploaded - no action taken.")
        SpecificationService.remove_spec()
        self.stdout.write("Assessment specification was removed.")

    def add_arguments(self, parser: CommandParser) -> None:
        sub = parser.add_subparsers(
            dest="command",
            description="""
                Perform tasks related to uploading/downloading/deleting
                of a specification.
            """,
        )
        sub.add_parser("status", help="Show details of current specification")
        sp_U = sub.add_parser("upload", help="Upload a specification")
        sp_D = sub.add_parser("download", help="Download the current specification")
        sp_D.add_argument(
            "dest", type=str, nargs="?", help="Where to download specification toml"
        )
        sub.add_parser("remove", help="Remove the specification from the server")

        sp_U.add_argument(
            "test_spec.toml", type=str, help="Default file to upload, or specify one"
        )

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_status()
        elif options["command"] == "upload":
            self.upload_spec(options["test_spec.toml"])
        elif options["command"] == "download":
            self.download_spec(options["dest"])
        elif options["command"] == "remove":
            self.remove_spec()
        else:
            self.print_help("manage.py", "plom_preparation_spec")

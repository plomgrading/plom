# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.db import transaction

from Papers.services import SpecificationService
from SpecCreator.services import SpecificationUploadService
from SpecCreator.services.spec_upload import SpecExistsException

from ...services import PQVMappingService


class Command(BaseCommand):
    help = "Displays the current status of the spec, and allows user to upload/download/remove."

    def show_status(self):
        if not SpecificationService.is_there_a_spec():
            self.stdout.write("No valid test spec present")
            return

        toml_text = SpecificationService.get_the_spec_as_toml()
        self.stdout.write("A valid test spec is present:")
        self.stdout.write("#" * 40)
        self.stdout.write(f"{toml_text}")
        self.stdout.write("#" * 40)

    def download_spec(self, dest=None):
        if not SpecificationService.is_there_a_spec():
            self.stderr.write("No valid test spec present")
            return

        spec_dict = SpecificationService.get_the_spec()
        self.stdout.write(
            f"A valid test spec is present: shortname {spec_dict['name']}"
        )
        if dest is None:
            fname = Path(slugify(spec_dict["name"]) + "_spec.toml")
        else:
            fname = Path(dest)
        self.stdout.write(f"Writing test spec toml to {fname}")
        if fname.exists():
            self.stderr.write(f"File {fname} already present - not overwriting.")
            return
        with open(fname, "w") as f:
            f.write(SpecificationService.get_the_spec_as_toml())

    def upload_spec(self, spec_file):
        try:
            service = SpecificationUploadService(toml_file_path=spec_file)
        except ValueError as e:
            raise CommandError(f"Cannot save test specification: {e}") from e

        with transaction.atomic():
            try:
                service.save_spec()
            except SpecExistsException as e:
                input_loop_done = False
                while not input_loop_done:
                    print(e)
                    confirm = input(
                        "There is already a spec present. Do you wish to overwrite? (y/n)"
                    ).casefold()
                    if confirm == "y":
                        service.delete_spec()
                        service.save_spec()
                    elif confirm == "n":
                        return
                    input_loop_done = True
            except RuntimeError as e:
                raise CommandError("Cannot save test specification.") from e

        self.stdout.write("Test specification validated.")

        self.stdout.write("Test specification uploaded to server.")

    def remove_spec(self):
        if not SpecificationService.is_there_a_spec():
            self.stdout.write("No specification uploaded - no action taken.")
            return

        service = SpecificationUploadService()
        try:
            # use more informative exceptions from inside the function
            if service.can_spec_be_modified(raise_exception=True):
                self.stdout.write("Removing the test specification.")
                service.delete_spec()
            else:
                raise CommandError("Cannot delete specification.")
        except ValueError as e:
            raise CommandError(e)

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Perform tasks related to uploading/downloading/deleting of a classlist.",
        )
        sub.add_parser("status", help="Show details of current test spec")
        sp_U = sub.add_parser("upload", help="Upload a test spec")
        sp_D = sub.add_parser(
            "download", help="Download the current test spec (if is valid)"
        )
        sp_D.add_argument(
            "dest", type=str, nargs="?", help="Where to download the test spec toml"
        )
        sub.add_parser("remove", help="Remove the current test spec from the server")

        sp_U.add_argument(
            "test_spec_toml", type=str, help="The test spec toml to upload"
        )

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_status()
        elif options["command"] == "upload":
            self.upload_spec(
                options["test_spec_toml"],
            )
        elif options["command"] == "download":
            self.download_spec(options["dest"])
        elif options["command"] == "remove":
            self.remove_spec()
        else:
            self.print_help("manage.py", "plom_preparation_test_spec")

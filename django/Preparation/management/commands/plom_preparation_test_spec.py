from django.core.management.base import BaseCommand, CommandError

from TestCreator.services import TestSpecService, TestSpecGenerateService
from Preparation.services import PQVMappingService

import toml


class Command(BaseCommand):
    help = "Displays the current status of the spec, and allows user to upload/download/remove."

    def show_status(self):
        speck = TestSpecService()
        gen = TestSpecGenerateService(speck)
        spec_dict = gen.generate_spec_dict()
        toml_text = toml.dumps(spec_dict)

        if speck.is_specification_valid():
            self.stdout.write("A valid test spec is present:")
            self.stdout.write("#" * 40)
            self.stdout.write(f"{toml_text}")
            self.stdout.write("#" * 40)
        else:
            self.stdout.write("No valid test spec present")

    def download_spec(self):
        speck = TestSpecService()
        gen = TestSpecGenerateService(speck)
        spec_dict = gen.generate_spec_dict()
        toml_text = toml.dumps(spec_dict)

        if speck.is_specification_valid():
            self.stdout.write("A valid test spec is present")
            self.stdout.write(f"{toml_text}")
        else:
            self.stderr.write("No valid test spec present")

    def upload_spec(self, spec_toml):
        self.stdout.write(
            "Not yet implemented - need to hook in plom spec validation things"
        )

    def remove_spec(self):
        pqvs = PQVMappingService()
        if pqvs.is_there_a_pqv_map():
            self.stderr.write("Warning - there is question-version mapping present.")
            self.stderr.write(
                "The test-spec cannot be deleted until that is removed; use the plom_preparation_qvmap command to remove the qv-mapping."
            )
            return
        speck = TestSpecService()
        self.stdout.write("Removing the test specification.")
        speck.reset_specification()

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Perform tasks related to uploading/downloading/deleting of a classlist.",
        )
        sp_S = sub.add_parser("status", help="Show details of current test spec")
        sp_U = sub.add_parser("upload", help="Upload a test spec")
        sp_D = sub.add_parser(
            "download", help="Download the current test spec (if is valid)"
        )
        sp_R = sub.add_parser("remove", help="Remove the current test spec the server")

        sp_U.add_argument(
            "test_spec_toml", type=str, help="The test spec toml to upload"
        )

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_status()
        elif options["command"] == "upload":
            self.upload_test_spec(
                spec_toml=options["test_spec_toml"],
            )
        elif options["command"] == "download":
            self.download_spec()
        elif options["command"] == "remove":
            self.remove_spec()
        else:
            self.print_help("manage.py", "plom_preparation_test_spec")

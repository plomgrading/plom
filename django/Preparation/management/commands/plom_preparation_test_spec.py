from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from TestCreator.services import TestSpecService, TestSpecGenerateService
from Preparation.services import PQVMappingService
from plom import SpecVerifier

import copy
import fitz
from pathlib import Path
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

        if not speck.is_specification_valid():
            self.stderr.write("No valid test spec present")
            return

        self.stdout.write(
            "A valid test spec is present - shortname = {spec_dict['name']}"
        )
        fname = Path(slugify(spec_dict["name"]) + "_spec.toml")
        self.stdout.write(f"Writing test spec toml to {fname}")
        if fname.exists():
            self.stderr.write(f"File {fname} already present - cannot overwrite.")
            return
        with open(fname, "w") as fh:
            toml.dump(spec_dict, fh)

    def upload_spec(self, spec_file, pdf_file):
        speck = TestSpecService()
        if speck.is_specification_valid():
            self.stderr.write("There is already a spec present. Cannot proceed with upload.")
            return

        spec_path = Path(spec_file)
        if spec_path.exists() is False:
            self.stderr.write(f"Cannot open {spec_path}.")
            return
        try:
            with open(spec_path) as fh:
                spec_dict = toml.load(fh)
        except toml.TomlDecodeError as err:
            self.stderr.write(f"Cannot decode the toml file - {err}")
            return
        self.stdout.write(f"From {spec_path} read spec dict = {spec_dict}")

        # plom wants numberToProduce to be set - so we set a dummy value here by hand
        # also make sure it is not set to zero
        # TODO - make a more elegant solution here.
        if 'numberToProduce' not in spec_dict:
            spec_dict['numberToProduce'] = 1
        elif spec_dict['numberToProduce'] == 0:
            spec_dict['numberToProduce'] = 1
            
        # CAREFUL - vlad will change the underly dict, so pass it a copy
        vlad = SpecVerifier(copy.deepcopy(spec_dict))

        try:
            vlad.verifySpec()
            validated_spec = vlad.spec
        except ValueError as err:
            self.stderr.write(f"There was an error validating the spec: {err}")
            return
        
        self.stdout.write("Test specification validated.")

        pdf_path = Path(pdf_file)
        if pdf_path.exists() is False:
            self.stderr.write(f"Cannot open {pdf_path}.")
            return
        pdf_doc = fitz.Document(pdf_path)
        if pdf_doc.page_count != spec_dict['numberOfPages']:
            self.stderr.write(f"Sample pdf does not match the test specification. PDF has {pdf_doc.page_count}, but spec indicates {spec_dict['numberOfPages']}.")
        self.stdout.write("Sample pdf has correct page count - matches specification.")

        # Load in the validated spec from vlad - not the original toml. This will be correctly populated
        # with any optional keys etc. See issue #88 
        speck.read_spec_dict(validated_spec, pdf_path)
        self.stdout.write("Test specification and sample pdf uploaded to server.")


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
        sp_U.add_argument(
            "source_pdf", type=str, help="A source PDF of the test."
        )

    def handle(self, *args, **options):
        if options["command"] == "status":
            self.show_status()
        elif options["command"] == "upload":
            self.upload_spec(
                options["test_spec_toml"],
                options["source_pdf"],
            )
        elif options["command"] == "download":
            self.download_spec()
        elif options["command"] == "remove":
            self.remove_spec()
        else:
            self.print_help("manage.py", "plom_preparation_test_spec")

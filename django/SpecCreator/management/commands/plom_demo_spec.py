import toml
import copy
import fitz
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from plom.specVerifier import SpecVerifier

from SpecCreator.services import StagingSpecificationService, ReferencePDFService
from Papers.services import SpecificationService


class Command(BaseCommand):
    """
    Push simple demo data to the test specification creator app.
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
        staged_spec_service = StagingSpecificationService()
        valid_spec_service = SpecificationService()
        ref_service = ReferencePDFService()
        if options["clear"]:
            if staged_spec_service.not_empty():
                self.stdout.write("Clearing test specification...")
                staged_spec_service.clear_questions()
                ref_service.delete_pdf()
                staged_spec_service.reset_specification()

                if valid_spec_service.is_there_a_spec():
                    valid_spec_service.remove_spec()
                self.stdout.write("Test specification cleared.")
            else:
                self.stdout.write("No specification uploaded.")
        else:
            if valid_spec_service.is_there_a_spec() or staged_spec_service.not_empty():
                self.stderr.write(
                    "Test specification data already present. Run manage.py plom_demo_spec --clear to clear the current specification."
                )
            else:
                self.stdout.write("Writing test specification...")
                curr_path = (
                    settings.BASE_DIR / "SpecCreator" / "management" / "commands"
                )
                toml_path = curr_path / "demo_spec.toml"
                data = toml.load(toml_path)
                pdf_path = curr_path / "demo_version1.pdf"

                # upload reference PDF
                with open(pdf_path, "rb") as f:
                    fitzed_doc = fitz.Document(pdf_path)
                    n_pdf_pages = fitzed_doc.page_count
                    pdf_doc = SimpleUploadedFile("spec_reference.pdf", f.read())

                ref_service.new_pdf(
                    staged_spec_service, "spec_reference.pdf", n_pdf_pages, pdf_doc
                )

                # verify spec, stage + save to DB
                try:
                    staged_spec_service.create_from_dict(data)
                    valid_spec = staged_spec_service.get_valid_spec_dict()

                    if options["publicCode"]:
                        code = options["publicCode"]
                        valid_spec["publicCode"] = code

                    valid_spec_service.store_validated_spec(valid_spec)
                    self.stdout.write("Demo test specification uploaded!")
                    self.stdout.write(str(valid_spec_service.get_the_spec()))
                except ValueError as e:
                    self.stderr.write(e)

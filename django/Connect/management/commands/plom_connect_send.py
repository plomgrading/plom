from django.core.management.base import BaseCommand

from Connect.services import CoreConnectionService
from TestCreator.services import TestSpecService, TestSpecGenerateService


class Command(BaseCommand):
    help = "Send test specification or classlist to a Plom-classic server. Or, send a QV-map and initialize the database."

    def send_test_spec(self):
        spec = TestSpecService()
        if not spec.is_specification_valid():
            self.stderr.write(
                "Valid test specification not found. Please upload one using plom_preparation_test_spec."
            )
            return

        spec_dict = TestSpecGenerateService(spec).generate_spec_dict()

        core = CoreConnectionService()
        if not core.is_there_a_valid_connection():
            self.stderr.write(
                "Valid Plom-classic connection not found. Please test with plom_connect_test."
            )
            return

        core.send_test_spec(spec_dict)
        return spec_dict

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Send information to Plom-classic server."
        )

        sp_testspec = sub.add_parser("test_spec", help="Send test specification to Plom-classic.")

    def handle(self, *args, **options):
        if options['command'] == "test_spec":
            self.stdout.write(
                "Sending test specification to Plom-classic..."
            )
            spec = self.send_test_spec()
            if spec:
                self.stdout.write(
                    "Specification sent!"
                )
        else:
            self.print_help("manage.py", "plom_connect_send")
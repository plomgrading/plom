import toml
from django.core.management.base import BaseCommand
from django.conf import settings

from SpecCreator.services import StagingSpecificationService, ReferencePDFService


class Command(BaseCommand):
    """
    Push simple demo data to the test specification creator app.
    Also, can clear the current test specification. 
    """
    help = "Create a demo test specification."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear an existing test specification.',
        )

    def handle(self, *args, **options):
        spec = StagingSpecificationService()
        ref_service = ReferencePDFService()
        if options['clear']:
            if spec.is_there_some_spec_data():
                self.stdout.write('Clearing test specification...')
                spec.clear_questions()
                ref_service.delete_pdf()
                spec.reset_specification()
                self.stdout.write('Test specification cleared.')
            else:
                self.stdout.write('No specification uploaded.')
        else:
            if spec.is_there_some_spec_data():
                self.stderr.write('Test specification data already present. Run manage.py plom_demo_spec --clear to clear the current specification.')
            else:
                self.stdout.write('Writing test specification...')
                curr_path = settings.BASE_DIR / 'SpecCreator' / 'management' / 'commands'
                toml_path = curr_path / 'demo_spec.toml'
                data = toml.load(toml_path)
                pdf_path = curr_path / 'demo_version1.pdf'
                spec.create_from_dict(data)
                with open(pdf_path, 'rb') as f:
                    ref_service.new_pdf(spec, spec.get_short_name_slug(), spec.get_n_pages(), f.read())
                self.stdout.write('Demo test specification uploaded!')
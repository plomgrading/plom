import toml
from django.core.management.base import BaseCommand
from django.conf import settings
from ... import services


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
        if options['clear']:
            if services.is_there_some_spec_data():
                self.stdout.write('Clearing test specification...')
                services.clear_questions()
                services.delete_pdf()
                services.reset_spec()
                services.reset_progress()
                self.stdout.write('Test specification cleared.')
            else:
                self.stdout.write('No specification uploaded.')
        else:
            if services.is_there_some_spec_data():
                self.stderr.write('Test specification data already present. Run manage.py plom_demo_spec --clear to clear the current specification.')
            else:
                self.stdout.write('Writing test specification...')
                curr_path = settings.BASE_DIR / 'TestCreator' / 'management' / 'commands'
                toml_path = curr_path / 'demo_spec.toml'
                data = toml.load(toml_path)
                pdf_path = curr_path / 'demo_version1.pdf'
                services.read_spec_dict(data, pdf_path)
                self.stdout.write('Demo test specification uploaded!')
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Push simple demo data to the test specification creator app.
    Also, can clear the current test specification. 
    """
    help = "Create a demo test specification."

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        print('Handled successfully!')
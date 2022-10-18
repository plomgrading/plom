from django.core.management.base import BaseCommand, CommandError

from Preparation.services import PrenameSettingService


class Command(BaseCommand):
    help = "Displays the current status of prenaming, and allows user to enable or disable it."

    def add_arguments(self, parser):
        grp = parser.add_mutually_exclusive_group()
        grp.add_argument(
            "--enable", action="store_true", help="Enable prenaming of papers"
        )
        grp.add_argument(
            "--disable", action="store_true", help="Disable prenaming of papers"
        )

    def handle(self, *args, **options):
        pss = PrenameSettingService()
        current_state = pss.get_prenaming_setting()

        # if enable or disable options given
        if options["enable"]:
            if current_state:
                print("Prenaming already enabled")
            else:
                pss.set_prenaming_setting(True)
                print("Enabling prenaming")
            return
        if options["disable"]:
            if not current_state:
                print("Prenaming already disabled")
            else:
                pss.set_prenaming_setting(False)
                print("Disabling prenaming")
            return

        # otherwise print current state
        if current_state:
            self.stdout.write("Prenaming is currently enabled")
        else:
            self.stdout.write("Prenaming is currently disabled")

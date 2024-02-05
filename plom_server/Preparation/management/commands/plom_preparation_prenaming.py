# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.core.management.base import BaseCommand, CommandError

from ...services import PrenameSettingService, PapersPrinted


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

        if not (options["enable"] or options["disable"]):
            # print current state
            if current_state:
                self.stdout.write("Prenaming is currently enabled")
            else:
                self.stdout.write("Prenaming is currently disabled")
            return

        if PapersPrinted.have_papers_been_printed():
            raise CommandError("Papers have been printed. You cannot change prenaming")

        # if enable or disable options given
        if options["enable"]:
            if current_state:
                print("Prenaming already enabled")
            else:
                pss.set_prenaming_setting(True)
                print("Enabling prenaming")

        elif options["disable"]:
            if not current_state:
                print("Prenaming already disabled")
            else:
                pss.set_prenaming_setting(False)
                print("Disabling prenaming")

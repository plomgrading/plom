# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer

from tqdm import tqdm

from django.core.management.base import BaseCommand
from django.core.management import call_command

from Scan.services import ManageScanService


class Command(BaseCommand):
    """Build solutions for all scanned papers."""

    def handle(self, *args, **options):
        # get a list of all complete papers
        complete_paper_keys = ManageScanService().get_all_completed_test_papers().keys()
        for n, pn in tqdm(
            enumerate(complete_paper_keys),
            desc="Building solution pdfs for each paper.",
        ):
            call_command("plom_build_soln", pn, "-w")

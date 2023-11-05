# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Colin B. Macdonald

from django.core.management.base import BaseCommand

from ...services import ReportPDFService


class Command(BaseCommand):
    """Generates a PDF report of the marking progress."""

    help = """Generates a PDF report of the marking progress.

    Report is saved as a pdf in the server `plom_server` directory.

    Requires matplotlib, pandas, seaborn, and weasyprint. If calling on demo
    data, run `python manage.py plom_demo --randomarker` first.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--versions",
            action="store_true",
            help="Include version in report graphics (optional bool)",
        )

    def handle(self, *args, **options):
        print("Building report.")
        graphs_message = """Graphs to generate:
    1. Histogram of total marks
    2. Histogram of marks by question
    3. Correlation heatmap
    4. Histograms of grades by marker by question
    5. Histograms of time spent marking each question
    6. Scatter plots of time spent marking vs mark given
    7. Box plots of grades given by marker by question
    8. Line graph of average mark by question

Generating..."""
        print(graphs_message)

        versions = options["versions"]

        d = ReportPDFService.pdf_builder(versions, verbose=True, _use_tqdm=True)

        print(f"Writing to {d['filename']}...")
        with open(d["filename"], "wb") as f:
            f.write(d["bytes"])
        print("Finished saving report.")

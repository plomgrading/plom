# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2025-2026 Colin B. Macdonald
# Copyright (C) 2026 Deep Shah

from tabulate import tabulate
from time import sleep

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import MultipleObjectsReturned

from plom_server.Rectangles.services import RectangleExtractor
from plom_server.Papers.services import SpecificationService
from ...services import (
    HEATMAP_MODE_FRESH,
    HEATMAP_MODE_RESUME,
    HeatmapMode,
    IDReaderService,
)


class Command(BaseCommand):
    """Commandline tool for running and managing the results of the ID-reader.

    Note --- at present only works for ID page version 1.
    """

    def get_the_rectangle(self) -> dict[str, float]:
        id_page_number = SpecificationService.get_id_page_number()
        # Always searches version 1
        rex = RectangleExtractor(1, id_page_number)
        # note that this rectangle is stated [0,1] coords relative to qr-code positions
        region = None  # we are not specifying a region to search.
        initial_rectangle = rex.get_largest_rectangle_contour(region)
        if initial_rectangle is None:
            raise CommandError("Could not find id box rectangle")
        self.stdout.write(f"Found id box rectangle at = {initial_rectangle}")
        return initial_rectangle

    def run_the_reader(
        self, user_obj, rectangle: dict[str, float], *, heatmap_mode: HeatmapMode
    ) -> None:
        try:
            self.stdout.write(f"Running the ID reader using {heatmap_mode} heatmaps")
            IDReaderService.run_id_reader_in_background_via_huey(
                user_obj,
                {1: rectangle},
                heatmap_mode=heatmap_mode,
            )
        except MultipleObjectsReturned:
            raise CommandError("The ID reader is already running.")

    def delete_all_ML_ID_predictions(self) -> None:
        self.stdout.write("Deleting all machine learning ID predictions.")
        IDReaderService.delete_all_ML_ID_predictions()

    def wait_for_reader(self) -> None:
        self.stdout.write("Waiting for any background ID reader processes to finish")
        while True:
            status = IDReaderService.get_id_reader_background_chore_status()
            self.stdout.write(f"Status = {status['status']}: {status['message']}")
            if status["status"] in ("Starting", "Queued", "Running"):
                self.stdout.write("Waiting....")
                sleep(2)
            elif status["status"] == "Error":
                raise CommandError(f"Background ID reader failed: {status['message']}")
            else:
                break

    def list_predictions(self) -> None:
        all_predictions = IDReaderService.get_ID_predictions()
        if not all_predictions:
            self.stderr.write("No ID predictions")
            return
        rows = []
        for pn, dat in all_predictions.items():
            rows.append({"paper_number": pn})
            rows[-1].update(
                {X["predictor"]: (X["student_id"], X["certainty"]) for X in dat}
            )
        self.stdout.write(tabulate(rows, headers="keys", tablefmt="simple_outline"))

    def add_arguments(self, parser):
        g = parser.add_mutually_exclusive_group()
        g.add_argument(
            "--rectangle", action="store_true", help="Just get the ID-box rectangle"
        )
        g.add_argument("--run", action="store_true", help="Run the ID-reader")
        g.add_argument(
            "--run-use-existing-heatmaps",
            action="store_true",
            help="""
               Run the ID-rder, but try to reuse any existing saved
               digit "heatmaps" where possible
            """,
        )
        g.add_argument("--delete", action="store_true", help="Delete any predictions")
        g.add_argument(
            "--wait", action="store_true", help="Wait for any running ID-reader process"
        )
        g.add_argument(
            "--list", action="store_true", help="List any existing predictions"
        )

    def handle(self, *args, **kwargs):
        username = "manager"  # TODO - replace with general option for username
        # Fetch the user object based on the username
        User = get_user_model()
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist")

        if kwargs["rectangle"]:
            the_id_box_rectangle = self.get_the_rectangle()
        elif kwargs["run"]:
            the_id_box_rectangle = self.get_the_rectangle()
            self.run_the_reader(
                user_obj, the_id_box_rectangle, heatmap_mode=HEATMAP_MODE_FRESH
            )
        elif kwargs["run_use_existing_heatmaps"]:
            the_id_box_rectangle = self.get_the_rectangle()
            self.run_the_reader(
                user_obj, the_id_box_rectangle, heatmap_mode=HEATMAP_MODE_RESUME
            )
        elif kwargs["list"]:
            self.list_predictions()
        elif kwargs["wait"]:
            self.wait_for_reader()
        elif kwargs["delete"]:
            self.delete_all_ML_ID_predictions()
        else:
            self.print_help("manage.py", "plom_run_id_reader")

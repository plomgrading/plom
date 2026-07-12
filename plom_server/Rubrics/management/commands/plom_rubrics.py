# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2026 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024-2025 Andrew Rechnitzer

import pathlib
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from tabulate import tabulate

from ...services import RubricService


class Command(BaseCommand):
    """Commands for rubrics manipulation."""

    help = "Manipulate rubrics"

    def init_rubrics_cmd(self):
        return RubricService.init_rubrics()

    def download_rubrics_to_file(
        self,
        filename: None | str | pathlib.Path,
        *,
        verbose: bool = True,
        question_idx: int | None = None,
    ) -> None:
        """Download the rubrics from a server and save them to a file.

        Args:
            filename: What filename to save to or None to display to stdout.
                The extension is used to determine what format, supporting:
                `.json`, `.toml`, and `.csv`.
                If no extension is included, default to `.toml`.

        Keyword Args:
            verbose: print stuff.
            question_idx: download for question index, or ``None`` for all.

        Returns:
            None: but saves a file as a side effect.
        """
        service = RubricService()

        if not filename:
            rubrics = service.get_rubrics_as_dicts(question_idx=question_idx)
            if not rubrics and question_idx:
                self.stdout.write(f"No rubrics for question index {question_idx}")
                return
            if not rubrics:
                self.stdout.write("No rubrics yet")
                return
            self.stdout.write(tabulate(rubrics, headers="keys"))
            return

        filename = Path(filename)
        if filename.suffix.casefold() not in (".json", ".toml", ".csv"):
            filename = filename.with_suffix(filename.suffix + ".toml")
        suffix = filename.suffix[1:]

        if verbose:
            self.stdout.write(f'Saving server\'s current rubrics to "{filename}"')

        with open(filename, "w") as f:
            data = service.get_rubric_data(suffix, question_idx=question_idx)
            f.write(data)

    def upload_rubrics_from_file(self, filename):
        """Load rubrics from a file and upload them to the server.

        Args:
            filename (pathlib.Path): A filename to load from.  Types  `.json`,
                `.toml`, and `.csv` are supported.  If no suffix is included
                we'll try to append `.toml`.

        TODO: anything need done about missing fields etc?  See also Issue #2640.
        Currently RubricService.create_rubric() raises a KeyError on missing fields.
        """
        if filename.suffix.casefold() not in (".json", ".toml", ".csv"):
            raise CommandError(f"Unsupported file type: {filename}")
        suffix = filename.suffix

        if suffix in (".json", ".csv"):
            f = open(filename, "r")
            data = f.read()
        elif suffix == ".toml":
            f = open(filename, "rb")
            data = f.read().decode("utf-8")
        else:
            raise CommandError(f"Unsupported file type: {filename}")

        rubrics = RubricService.create_rubrics_from_file_data(
            data, suffix[1:], _bypass_permissions=True
        )
        return len(rubrics)

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Various tasks about rubrics.",
        )

        _ = sub.add_parser(
            "init",
            help="Initialize the rubric system with system rubrics",
            description="Initialize the rubric system with system rubrics.",
        )

        sp_push = sub.add_parser(
            "push",
            help="Add pre-build rubrics",
            description="""
                Add pre-made rubrics to the server.  Your graders will be able to
                build their own rubrics but if you have premade rubrics you can
                add them here.
            """,
        )
        sp_push.add_argument(
            "username",
            type=str,
            help="Name of user who is pushing the demo rubrics.",
        )
        sp_push.add_argument(
            "file",
            nargs="?",
            help="""
                Upload a pre-build list of rubrics from this file.
                This can be a .json, .toml or .csv file.
            """,
        )
        sp_pull = sub.add_parser(
            "pull",
            help="Get the current rubrics from the server.",
            description="Get the current rubrics from a running server.",
        )
        sp_pull.add_argument(
            "file",
            nargs="?",
            help="""
                Dump the current rubrics into a file,
                which can be a .toml, .json, or .csv.
                Defaults to .toml if no extension specified.
                Default to the stdout if no file provided.
            """,
        )
        sp_pull.add_argument(
            "--question",
            type=int,
            metavar="N",
            help="Get rubrics only for question (index) N, or all rubrics if omitted.",
        )
        s = sub.add_parser(
            "fractional_delta",
            help="Add plus/minus 1/N delta rubrics",
            description="""
                Add \N{PLUS-MINUS SIGN}1/N delta rubrics for all questions,
                for whichever fractions are currently enabled on the server.
                Any existing rubrics will be skipped.
            """,
        )
        s.add_argument(
            "username",
            type=str,
            help="Name of user to associate with the fractional delta rubrics",
        )

    def handle(self, *args, **opt):
        if opt["command"] == "init":
            try:
                if self.init_rubrics_cmd():
                    self.stdout.write(self.style.SUCCESS("rubric system initialized"))
                else:
                    raise CommandError("rubric system already initialized")
            except ValueError as e:
                raise CommandError(e)

        elif opt["command"] == "push":
            f = Path(opt["file"])
            N = self.upload_rubrics_from_file(f)
            self.stdout.write(self.style.SUCCESS(f"Added {N} rubrics from {f}"))

        elif opt["command"] == "fractional_delta":
            try:
                user = User.objects.get(username__iexact=opt["username"])
            except User.DoesNotExist as e:
                raise CommandError(e) from e
            try:
                n = RubricService.build_fractional_delta_rubrics(user)
                self.stdout.write(
                    self.style.SUCCESS(f"Added {n} fractional delta rubrics")
                )
            except ValueError as e:
                raise CommandError(e)
        else:
            self.print_help("manage.py", "plom_rubrics")

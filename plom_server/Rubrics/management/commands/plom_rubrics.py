# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2026 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024-2025 Andrew Rechnitzer

import pathlib
import sys
from importlib import resources
from pathlib import Path

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

# try to avoid importing Pandas unless we use specific functions: Issue #2154
# import pandas

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from rest_framework import serializers
from tabulate import tabulate

import plom

from plom_server.Papers.services import SpecificationService
from ...services import RubricService


class Command(BaseCommand):
    """Commands for rubrics manipulation."""

    help = "Manipulate rubrics"

    def upload_demo_rubrics(
        self, username: str, *, _numquestions: int | None = None
    ) -> int:
        """Load some demo rubrics and upload to server.

        Args:
            username: rubrics need to be associated to a rubric.

        Keyword Args:
            _numquestions: how many questions should we build for.
                Get it from the spec if omitted / None.

        Returns:
            The number of rubrics uploaded.

        The demo data is a bit sparse: we fill in missing pieces and
        multiply over questions.

        TODO: this is somewhat deprecated and might be drifting away
        from the "other" demo rubric stuff in Launcher.
        """
        if _numquestions is None:
            question_indices = SpecificationService.get_question_indices()
        else:
            question_indices = list(range(1, _numquestions + 1))

        with (resources.files(plom) / "demo_rubrics.toml").open("rb") as f:
            # MyPy complains incompatible type "IO[bytes]" expected "BinaryIO"
            rubrics_in = tomllib.load(f)["rubric"]  # type: ignore[arg-type]
        rubrics = []
        for rub in rubrics_in:
            if not rub.get("kind"):
                if rub["delta"] == ".":
                    rub["kind"] = "neutral"
                    rub["value"] = 0
                    rub["out_of"] = 0
                elif rub["delta"].startswith("+") or rub["delta"].startswith("-"):
                    rub["kind"] = "relative"
                    rub["value"] = int(rub["delta"])
                    rub["out_of"] = 0  # unused for relative
                else:
                    raise CommandError(
                        f'not sure how to map "kind" for rubric:\n  {rub}'
                    )
            rub["display_delta"] = rub["delta"]
            rub.pop("delta")

            rub["username"] = username

            # some mangling because client still uses "question"
            if "question_index" not in rub.keys():
                rub["question_index"] = rub.pop("question")

            # Multiply rubrics w/o questions, avoids repetition in demo file
            if rub.get("question_index") is None:
                for q in question_indices:
                    r = rub.copy()
                    r["question_index"] = q
                    rubrics.append(r)
            else:
                rubrics.append(rub)

        user = User.objects.get(username=username)
        for rubric in rubrics:
            try:
                RubricService.create_rubric(rubric, creating_user=user)
            except KeyError as e:
                raise CommandError(f"{e} field(s) missing from rubrics file.")
            except serializers.ValidationError as e:
                raise CommandError(e.args[0])
            except ValueError as e:
                raise CommandError(e)
        return len(rubrics)

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

        TODO: in legacy, there is logic about HAL vs Manager about what to upload.
        There is also some incorrect logic about absolute rubrics being always
        autogenerated.  See `upload_rubrics` in `push_pull_rubrics.py`.
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
            data, suffix[1:], by_system=True
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
        group = sp_push.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "file",
            nargs="?",
            help="""
                Upload a pre-build list of rubrics from this file.
                This can be a .json, .toml or .csv file.
            """,
        )
        group.add_argument(
            "--demo",
            action="store_true",
            help="Upload an auto-generated rubric list for demos.",
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
        sp_half = sub.add_parser(
            "half",
            help="Add plus/minus half-mark rubrics",
            description="""
                Add plus/minus half-mark rubrics to the system for all questions.""",
        )
        sp_half.add_argument(
            "username",
            type=str,
            help="Name of user who is enabling the half-mark rubrics",
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
            if opt["demo"]:
                N = self.upload_demo_rubrics(opt["username"])
                self.stdout.write(self.style.SUCCESS(f"Added {N} demo rubrics"))
                return
            f = Path(opt["file"])
            N = self.upload_rubrics_from_file(f)
            self.stdout.write(self.style.SUCCESS(f"Added {N} rubrics from {f}"))

        elif opt["command"] == "half":
            try:
                RubricService.build_half_mark_delta_rubrics(opt["username"])
                self.stdout.write(self.style.SUCCESS("Half-mark rubrics added."))
            except ValueError as e:
                raise CommandError(e)
        else:
            self.print_help("manage.py", "plom_rubrics")

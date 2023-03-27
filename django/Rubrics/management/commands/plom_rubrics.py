# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

import json
from pathlib import Path
import sys

# avoid hard dependency: loaded on demand if user writes csv file
# import pandas

from tabulate import tabulate

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib
import tomlkit

from django.core.management.base import BaseCommand, CommandError

from Rubrics.services import RubricService


class Command(BaseCommand):
    """Commands for rubrics manipulation."""

    help = "Manipulate rubrics"

    def upload_demo_rubrics(self, *, numquestions=3):
        """Load some demo rubrics and upload to server.

        Keyword Args:
            numquestions (int): how many questions should we build for.
                TODO: get number of questions from the server spec if
                omitted.

        The demo data is a bit sparse: we fill in missing pieces and
        multiply over questions.
        """
        with open(resources.files("plom") / "demo_rubrics.toml", "rb") as f:
            rubrics_in = tomllib.load(f)
        rubrics_in = rubrics_in["rubric"]
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

            # TODO: didn't need to do this on legacy, Issue #2640
            rub["username"] = "manager"
            rub["tags"] = ""
            rub["meta"] = ""

            # Multiply rubrics w/o question numbers, avoids repetition in demo file
            if rub.get("question") is None:
                for q in range(1, numquestions + 1):
                    r = rub.copy()
                    r["question"] = q
                    rubrics.append(r)
            else:
                rubrics.append(rub)

        service = RubricService()
        for rubric in rubrics:
            service.create_rubric(rubric)
        return len(rubrics)

    def init_rubrics_cmd(self):
        service = RubricService()
        return service.init_rubrics()

    def erase_all_rubrics_cmd(self):
        service = RubricService()
        return service.erase_all_rubrics()

    def download_rubrics_to_file(self, filename, *, verbose=True):
        """Download the rubrics from a server and save them to a file.

        Args:
            filename (None/str/pathlib.Path): A filename to save to.  The
                extension is used to determine what format, supporting:
                `.json`, `.toml`, and `.csv`.
                If no extension is included, default to `.toml`.
                If None, display on stdout.

        Keyword Args:
            verbose (bool):

        Returns:
            None: but saves a file as a side effect.
        """
        service = RubricService()
        # TODO: we need a way to get all, not filtered by question
        # TODO: maybe question=None?
        rubrics = service.get_rubrics_by_question(question=1)

        if not filename:
            self.stdout.write(tabulate(rubrics))  # headers="keys"
            return

        filename = Path(filename)
        if filename.suffix.casefold() not in (".json", ".toml", ".csv"):
            filename = filename.with_suffix(filename.suffix + ".toml")
        suffix = filename.suffix

        if verbose:
            self.stdout.write(f'Saving server\'s current rubrics to "{filename}"')

        with open(filename, "w") as f:
            if suffix == ".json":
                json.dump(rubrics, f, indent="  ")
            elif suffix == ".toml":
                tomlkit.dump({"rubric": rubrics}, f)
            elif suffix == ".csv":
                try:
                    import pandas
                except ImportError as e:
                    raise CommandError(f'CSV writing needs "pandas" library: {e}')

                df = pandas.json_normalize(rubrics)
                df.to_csv(f, index=False, sep=",", encoding="utf-8")
            else:
                raise CommandError(f'Don\'t know how to export to "{filename}"')

    def upload_rubrics_from_file(self, filename):
        """Load rubrics from a file and upload them to the server.

        Args:
            filename (pathlib.Path): A filename to load from.  Types  `.json`,
                `.toml`, and `.csv` are supported.  If no suffix is included
                we'll try to append `.toml`.

        TODO: anything need done about missing fields etc?  See also Issue #2640.
        """
        if filename.suffix.casefold() not in (".json", ".toml", ".csv"):
            filename = filename.with_suffix(filename.suffix + ".toml")
        suffix = filename.suffix

        if suffix == ".json":
            with open(filename, "r") as f:
                rubrics = json.load(f)
        elif suffix == ".toml":
            with open(filename, "rb") as f:
                rubrics = tomllib.load(f)["rubric"]
        elif suffix == ".csv":
            with open(filename, "r") as f:
                try:
                    import pandas
                except ImportError as e:
                    raise CommandError(f'CSV reading needs "pandas" library: {e}')

                df = pandas.read_csv(f)
                df.fillna("", inplace=True)
                # TODO: flycheck is whining about this to_json
                rubrics = json.loads(df.to_json(orient="records"))
        else:
            raise CommandError(f'Don\'t know how to import from "{filename}"')

        service = RubricService()
        for rubric in rubrics:
            # rubric.pop("id")
            service.create_rubric(rubric)
        return len(rubrics)

    def add_arguments(self, parser):
        sub = parser.add_subparsers(
            dest="command",
            description="Various tasks about rubrics.",
        )

        sub.add_parser(
            "init",
            help="Initialize the rubric system with system rubrics",
            description="Initialize the rubric system with system rubrics.",
        )

        sp_wipe = sub.add_parser(
            "wipe",
            help="Erase all rubrics, including system rubrics (CAREFUL)",
            description="""
                Erase all rubrics, including system rubrics.
                BE CAREFUL: this will remove any rubrics that markers have added.
            """,
        )
        sp_wipe.add_argument(
            "--yes", action="store_true", help="Don't ask for confirmation."
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

    def handle(self, *args, **opt):
        if opt["command"] == "init":
            if self.init_rubrics_cmd():
                self.stdout.write(self.style.SUCCESS("rubric system initialized"))
            else:
                raise CommandError("rubric system already initialized")

        elif opt["command"] == "wipe":
            self.stdout.write(self.style.WARNING("CAUTION: "), ending="")
            self.stdout.write("This will erase ALL rubrics on the server!")
            if not opt["yes"]:
                if input('  Are you sure?  (type "yes" to continue) ') != "yes":
                    return
            N = self.erase_all_rubrics_cmd()
            self.stdout.write(self.style.SUCCESS(f"{N} rubrics permanently deleted"))

        elif opt["command"] == "push":
            if opt["demo"]:
                N = self.upload_demo_rubrics()
                self.stdout.write(self.style.SUCCESS(f"Added {N} demo rubrics"))
                return
            f = Path(opt["file"])
            N = self.upload_rubrics_from_file(f)
            self.stdout.write(self.style.SUCCESS(f"Added {N} rubrics from {f}"))

        elif opt["command"] == "pull":
            self.download_rubrics_to_file(opt["file"])

        else:
            self.print_help("manage.py", "plom_rubrics")

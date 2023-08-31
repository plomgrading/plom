# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from tqdm import trange
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from Finish.services import ReassembleService
from Papers.services import PaperInfoService
from Papers.models import Paper


class Command(BaseCommand):
    """Generate reassembled test-papers with TA annotations from the command line."""

    help = "Create PDFs to return to students"

    def add_arguments(self, parser):
        parser.add_argument(
            "--testnum",
            type=int,
            nargs="?",
            help="Which test paper to reassemble (optional)",
        )
        parser.add_argument(
            "--save-path",
            type=Path,
            nargs="?",
            help="Path for saving reassembled papers (optional)",
        )
        parser.add_argument(
            "--zip",
            type=Path,
            nargs="?",
            help="Path for saving zip of reassembled papers (optional)",
        )

    def reassemble_one_paper(self, test_num, save_path="reassembled"):
        paper_service = PaperInfoService()
        if not paper_service.is_paper_database_populated():
            raise CommandError("Paper database is not populated - stopping.")
        if not paper_service.is_this_paper_in_database(test_num):
            raise CommandError(f"Paper number {test_num} does not exist - stopping.")

        paper = Paper.objects.get(paper_number=test_num)
        reassembler = ReassembleService()

        try:
            out_path = reassembler.reassemble_paper(paper, outdir=save_path)
            self.stdout.write(f"File written to {out_path.absolute()}")
        except ValueError as e:
            raise CommandError(e)

    def reassemble_all_papers(self, save_path="reassembled"):
        paper_service = PaperInfoService()
        if not paper_service.is_paper_database_populated():
            raise CommandError("Paper database is not populated - stopping.")

        papers = Paper.objects.all()
        reassembler = ReassembleService()
        for i in trange(1, len(papers) + 1, desc="Reassembly progress"):
            try:
                paper = papers.get(paper_number=i)
                out_path = reassembler.reassemble_paper(paper, outdir=save_path)
            except ValueError as e:
                self.stderr.write(f"Warning: {e}")
        self.stdout.write(f"Papers written to {out_path.parent.absolute()}")

    def download_zip(self, zip_path):
        zipper = ReassembleService().get_zipfly_generator("reassembled")
        if zip_path.exists():
            raise CommandError(f"File '{zip_path}' already exists.")
        with zip_path.open("wb") as fh:
            for chunk in zipper:
                fh.write(chunk)

    def handle(self, *args, **options):
        save_path = options["save_path"]
        test_num = options["testnum"]
        zip_path = options["zip"]
        if zip_path:
            self.stdout.write("Downloading zip of reassembled papers")
            self.download_zip(Path(zip_path))
        elif test_num:
            self.stdout.write(f"Reassembling paper {test_num}...")
            self.reassemble_one_paper(test_num, save_path=save_path)
        else:
            self.stdout.write("Reassembling all papers...")
            self.reassemble_all_papers(save_path=save_path)

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Andrew Rechnitzer

from dataclasses import dataclass
from pathlib import Path
from shutil import copy
from time import sleep
from typing import Optional, List

# sigh.... python dependent import of toml - sorry.
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings

from Identify.services import IDDirectService
from Launcher.services import DemoBundleCreationService, DemoHWBundleCreationService
from Scan.services import ScanService


# dataclasses used for compatibility with older demo services.
# TODO = get rid of the older demo services.
@dataclass()
class DemoBundleConfig:
    """A description of a demo bundle that can be generated using artificial data."""

    first_paper: int
    last_paper: int
    extra_page_papers: Optional[List[int]] = None
    scrap_page_papers: Optional[List[int]] = None
    garbage_page_papers: Optional[List[int]] = None
    wrong_version_papers: Optional[List[int]] = None
    duplicate_page_papers: Optional[List[int]] = None
    discard_pages: Optional[List[int]] = None


@dataclass()
class DemoHWBundleConfig:
    """A description of a demo homework bundle that can be generated using artificial data."""

    paper_number: int
    pages: List[List[int]]
    student_id: Optional[str] = None
    student_name: Optional[str] = None


@dataclass()
class DemoAllBundlesConfig:
    bundles: Optional[List[DemoBundleConfig]] = None
    hw_bundles: Optional[List[DemoHWBundleConfig]] = None


def _read_bundle_config(length: str) -> DemoAllBundlesConfig:
    demo_file_directory = settings.BASE_DIR / "Launcher/launch_scripts/demo_files"
    # read the config toml file
    if length == "quick":
        fname = "bundle_for_quick_demo.toml"
    elif length == "long":
        fname = "bundle_for_long_demo.toml"
    elif length == "plaid":
        fname = "bundle_for_plaid_demo.toml"
    else:
        fname = "bundle_for_demo.toml"
    with open(demo_file_directory / fname, "rb") as fh:
        try:
            config_dict = tomllib.load(fh)
        except tomllib.TOMLDecodeError as e:
            raise RuntimeError(e)
    return DemoAllBundlesConfig(**config_dict)


class Command(BaseCommand):
    """Build the mock scan paper bundles for the demo."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--length",
            action="store",
            choices=["quick", "normal", "long", "plaid"],
            default="normal",
            help="Describe length of demo",
        )
        parser.add_argument(
            "--action",
            action="store",
            choices=["build", "upload", "read", "push", "id_hw"],
            required=True,
        )

    def build_the_bundles(self, demo_config: DemoAllBundlesConfig) -> None:
        # at present the bundle-creator assumes that the
        # scrap-paper and extra-page pdfs are in media/papersToPrint
        # so we make a copy of them from static to there.
        src_dir = Path(settings.STATICFILES_DIRS[0])
        dest_dir = Path(settings.MEDIA_ROOT) / "papersToPrint"
        copy(src_dir / "extra_page.pdf", dest_dir)
        copy(src_dir / "scrap_paper.pdf", dest_dir)
        # TODO - get bundle-creator to take from static.

        if demo_config.bundles:
            DemoBundleCreationService().scribble_on_exams(demo_config)

        if demo_config.hw_bundles is not None:
            for bundle in demo_config.hw_bundles:
                # note that this service creates the bundle,
                # but after upload we have to ask it to
                # map pages to questions and to ID the paper
                DemoHWBundleCreationService().make_hw_bundle(bundle)

    def _wait_for_upload(self) -> None:
        scanner = ScanService()
        while True:
            bundle_status = scanner.are_bundles_mid_splitting()
            mid_split = [k for k, v in bundle_status.items() if v]
            done = [k for k, v in bundle_status.items() if not v]
            print(f"Uploaded bundles = {done}")
            if mid_split:
                print(f"Still waiting on {mid_split}")
                sleep(5)
            else:
                break

    def upload_the_bundles_and_wait(self, demo_config: DemoAllBundlesConfig) -> None:
        scanner_user = "demoScanner1"
        if demo_config.bundles is not None:
            for n in range(len(demo_config.bundles)):
                bundle_name = f"fake_bundle{n+1}.pdf"
                call_command(
                    "plom_staging_bundles", "upload", scanner_user, bundle_name
                )
                sleep(0.5)
        if demo_config.hw_bundles is not None:
            for bundle in demo_config.hw_bundles:
                paper_number = bundle["paper_number"]
                bundle_name = f"fake_hw_bundle_{paper_number}.pdf"
                call_command(
                    "plom_staging_bundles", "upload", scanner_user, bundle_name
                )
                sleep(0.5)
        self._wait_for_upload()

    def read_qr_codes_and_wait(self, demo_config: DemoAllBundlesConfig) -> None:
        if demo_config.bundles is not None:
            for n in range(len(demo_config.bundles)):
                bundle_name = f"fake_bundle{n+1}"
                call_command("plom_staging_bundles", "read_qr", bundle_name)
        # no qr codes in the hw bundles, but we map them
        # according to the config
        if demo_config.hw_bundles is not None:
            DemoHWBundleCreationService().map_homework_pages(
                homework_bundles=demo_config.hw_bundles
            )

        self._wait_for_qr_read()

    def _wait_for_qr_read(self) -> None:
        scanner = ScanService()
        while True:
            bundle_status = scanner.are_bundles_mid_qr_read()
            mid_split = [k for k, v in bundle_status.items() if v]
            done = [k for k, v in bundle_status.items() if not v]
            print(f"Read all qr codes in bundles = {done}")
            if mid_split:
                print(f"Still waiting on {mid_split}")
                sleep(2)
            else:
                break

    def push_and_wait(self):
        scanner_user = "demoScanner1"
        bundle_status = ScanService().are_bundles_perfect()
        perfect = [k for k, v in bundle_status.items() if v]
        cannot = [k for k, v in bundle_status.items() if not v]
        pushed = [k for k, v in ScanService().are_bundles_pushed().items() if v]
        for bundle in perfect:
            if bundle not in pushed:
                print(f"Pushing bundle {bundle}")
                call_command("plom_staging_bundles", "push", bundle, scanner_user)
                sleep(1)
        print(f"The following bundles were already pushed, and so skipped: {pushed}")
        print(f"The following bundles had issues, and so were skipped: {cannot}")

    def direct_id_hw(self, demo_config: DemoAllBundlesConfig):
        manager_user = "demoManager1"
        if demo_config.hw_bundles is None:
            return
        pushed = [k for k, v in ScanService().are_bundles_pushed().items() if v]
        for hw_bundle in demo_config.hw_bundles:
            paper_number = hw_bundle["paper_number"]
            bundle_name = f"fake_hw_bundle_{paper_number}"
            if bundle_name not in pushed:
                print(f"Cannot ID bundle {bundle_name} since it has not been pushed.")
                continue
            if "student_id" in hw_bundle and "student_name" in hw_bundle:
                sid = hw_bundle["student_id"]
                sname = hw_bundle["student_name"]
                print(
                    f"Direct ID of homework paper {paper_number} as student {sid} {sname}"
                )
                # use the _cmd here so that it looks up the username for us.
                IDDirectService().identify_direct_cmd(
                    manager_user, paper_number, sid, sname
                )
        pass

    def handle(self, *args, **options):
        demo_config = _read_bundle_config(options["length"])

        if options["action"] == "build":
            self.build_the_bundles(demo_config)
        elif options["action"] == "upload":
            self.upload_the_bundles_and_wait(demo_config)
        elif options["action"] == "read":
            self.read_qr_codes_and_wait(demo_config)
        elif options["action"] == "push":
            self.push_and_wait()
        elif options["action"] == "id_hw":
            self.direct_id_hw(demo_config)

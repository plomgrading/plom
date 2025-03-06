# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

from dataclasses import dataclass
from pathlib import Path
from shutil import copy2
from time import sleep
from typing import Optional, List, Dict, Any

# sigh.... python dependent import of toml - sorry.
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings

from plom_server.Identify.services import IDDirectService
from plom_server.Scan.services import ScanService
from ...services import DemoBundleCreationService, DemoHWBundleCreationService


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
    # The dataclasses above are not yet working because
    # dataclass init needs to be told explicitly to
    # handle sub-dataclasses via __post_init__.
    # TODO - fix this when we fix up pdf mucking
    bundles: Optional[List[Dict[str, Any]]] = None
    hw_bundles: Optional[List[Dict[str, Any]]] = None


def _read_bundle_config(length: str) -> DemoAllBundlesConfig:
    """Read and parse the appropriate demo bundle config file."""
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
        """Process and parse commandline arguments."""
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
            choices=["build", "upload", "read", "wait", "push", "id_hw"],
            required=True,
            help="""(build) demo bundles,
            (upload) demo bundles,
            (read) qr-codes in uploaded demo bundles,
            (wait) for background processing of upload and qr-code reading,
            (push) processed bundles from staging,
            (id_hw) ID pushed demo homework bundles.""",
        )
        parser.add_argument("--versioned-id", dest="versioned_id", action="store_true")

    def build_the_bundles(
        self, demo_config: DemoAllBundlesConfig, *, versioned_id=False
    ) -> None:
        """Build demo bundles as per the chosen demo-config."""
        # at present the bundle-creator assumes that the
        # scrap-paper and extra-page pdfs are in media/papersToPrint
        # so we make a copy of them from static to there.
        src_dir = Path(settings.STATICFILES_DIRS[0])
        dest_dir = Path(settings.MEDIA_ROOT) / "papersToPrint"
        copy2(src_dir / "extra_page.pdf", dest_dir)
        copy2(src_dir / "scrap_paper.pdf", dest_dir)
        # TODO - get bundle-creator to take from static.

        if demo_config.bundles:
            DemoBundleCreationService().scribble_on_exams(
                demo_config, versioned_id=versioned_id
            )

        if demo_config.hw_bundles is not None:
            for bundle in demo_config.hw_bundles:
                # note that this service creates the bundle,
                # but after upload we have to ask it to
                # map pages to questions and to ID the paper
                DemoHWBundleCreationService().make_hw_bundle(bundle)

    def upload_the_bundles(self, demo_config: DemoAllBundlesConfig) -> None:
        """Upload the created demo bundles, and wait for process to finish."""
        scanner_user = "demoScanner1"
        if demo_config.bundles is not None:
            for n in range(len(demo_config.bundles)):
                bundle_name = f"fake_bundle{n+1}.pdf"
                call_command(
                    "plom_staging_bundles", "upload", scanner_user, bundle_name
                )
                sleep(0.5)  # small sleep to not overwhelm huey's db
        if demo_config.hw_bundles is not None:
            for bundle in demo_config.hw_bundles:
                paper_number = bundle["paper_number"]
                bundle_name = f"fake_hw_bundle_{paper_number}.pdf"
                call_command(
                    "plom_staging_bundles", "upload", scanner_user, bundle_name
                )
                sleep(0.5)  # small sleep to not overwhelm huey's db

    def read_qr_codes_in_bundles(self, demo_config: DemoAllBundlesConfig) -> None:
        """Read QR-codes of the uploaded bundles, and wait for process to finish."""
        if demo_config.bundles is not None:
            for n in range(len(demo_config.bundles)):
                bundle_name = f"fake_bundle{n+1}"
                call_command("plom_staging_bundles", "read_qr", bundle_name)
                sleep(0.5)  # small sleep to not overwhelm huey's db
        # no qr codes in the hw bundles, but we map them
        # according to the config
        if demo_config.hw_bundles is not None:
            DemoHWBundleCreationService().map_homework_pages(
                homework_bundles=demo_config.hw_bundles
            )

    def push_and_wait(self):
        """Push staged bundles and wait for the process to finish.

        Note that only perfect bundles (no errors, and no missing data) are pushed.
        """
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
        """IDs the papers in HW bundles as per the demo config."""
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
                IDDirectService.identify_direct_cmd(
                    manager_user, paper_number, sid, sname
                )
        pass

    def handle(self, *args, **options):
        """Handle demo bundle, build, upload, read, push and hw-id."""
        demo_config = _read_bundle_config(options["length"])

        if options["action"] == "build":
            self.build_the_bundles(demo_config, versioned_id=options["versioned_id"])
        elif options["action"] == "upload":
            self.upload_the_bundles(demo_config)
        elif options["action"] == "read":
            self.read_qr_codes_in_bundles(demo_config)
        elif options["action"] == "push":
            self.push_and_wait()
        elif options["action"] == "id_hw":
            self.direct_id_hw(demo_config)

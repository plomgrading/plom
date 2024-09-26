# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from __future__ import annotations

import hashlib
from math import ceil
import pathlib
import tempfile
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q  # for queries involving "or", "and"
from django_huey import db_task

from plom.scan import QRextract
from plom.scan import render_page_to_bitmap, try_to_extract_image
from plom.scan.question_list_utils import canonicalize_page_question_map
from plom.tpv_utils import (
    parseTPV,
    parseExtraPageCode,
    getPaperPageVersion,
    isValidTPV,
    isValidExtraPageCode,
    isValidScrapPaperCode,
)

from Papers.services import ImageBundleService, SpecificationService
from Papers.models import Image
from Base.models import HueyTaskTracker
from ..models import (
    StagingBundle,
    StagingImage,
    StagingThumbnail,
    KnownStagingImage,
    ExtraStagingImage,
    DiscardStagingImage,
    PagesToImagesHueyTask,
    ManageParseQR,
)
from ..services.qr_validators import QRErrorService
from .image_process import PageImageProcessor
from ..services.util import (
    update_thumbnail_after_rotation,
    check_any_bundle_push_locked,
    check_bundle_object_is_neither_locked_nor_pushed,
)
from plom.plom_exceptions import PlomBundleLockedException, PlomPushCollisionException


class ScanService:
    """Functions for staging scanned test-papers."""

    def upload_bundle(
        self,
        uploaded_pdf_file: File,
        slug: str,
        user: User,
        timestamp: float,
        pdf_hash: str,
        number_of_pages: int,
        *,
        force_render: bool = False,
        read_after: bool = False,
    ) -> None:
        """Upload a bundle PDF and store it in the filesystem + database.

        Also, split PDF into page images + store in filesystem and database.
        Currently if that fails for any reason, the StagingBundle is still
        created.

        Args:
            uploaded_pdf_file (Django File): File-object containing the pdf
                (can also be a TemporaryUploadedFile or InMemoryUploadedFile).
            slug: Filename slug for the pdf.
            user (Django User): the user uploading the file
            timestamp (float): the timestamp of the time at which the file was uploaded
            pdf_hash: the sha256 of the pdf.
            number_of_pages: the number of pages in the pdf.

        Keyword Args:
            force_render: Don't try to extract large bitmaps; always
                render the page.
            read_after: Automatically read the qr codes from the bundle after
                upload+splitting is finished.

        Returns:
            None
        """
        # Warning: Issue #2888, and https://gitlab.com/plom/plom/-/merge_requests/2361
        # strange behaviour can result from relaxing this durable=True
        with transaction.atomic(durable=True):
            # create the bundle first, so it has a pk and
            # then give it the file and resave it.
            bundle_obj = StagingBundle.objects.create(
                slug=slug,
                user=user,
                timestamp=timestamp,
                pushed=False,
                force_page_render=force_render,
            )
            with uploaded_pdf_file.open() as fh:
                bundle_obj.pdf_file = File(fh, name=f"{timestamp}.pdf")
                bundle_obj.pdf_hash = pdf_hash
                bundle_obj.number_of_pages = number_of_pages
                bundle_obj.save()
        self.split_and_save_bundle_images(bundle_obj.pk, read_after=read_after)

    def upload_bundle_cmd(
        self,
        pdf_file_path: str | pathlib.Path,
        slug: str,
        username: str,
        timestamp: float,
        pdf_hash: str,
        number_of_pages: int,
    ) -> None:
        """Wrapper around upload_bundle for use by the commandline bundle upload command.

        Checks if the supplied username has permissions to access and upload scans.

        Args:
            pdf_file_path (pathlib.Path or str): the path to the pdf being uploaded
            slug (str): Filename slug for the pdf
            username (str): the username uploading the file
            timestamp (float): the timestamp of the datetime at which the file was uploaded
            pdf_hash (str): the sha256 of the pdf.
            number_of_pages (int): the number of pages in the pdf

        Returns:
            None
        """
        # username => user_object, if in scanner group, else exception raised.
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="scanner"
            )
        except ObjectDoesNotExist:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        with open(pdf_file_path, "rb") as fh:
            pdf_file_object = File(fh)

        self.upload_bundle(
            pdf_file_object,
            slug,
            user_obj,
            timestamp,
            pdf_hash,
            number_of_pages,
        )

    def split_and_save_bundle_images(
        self,
        bundle_pk: int,
        *,
        number_of_chunks: int = 16,
        read_after: bool = False,
    ) -> None:
        """Read a PDF document and save page images to filesystem/database.

        Args:
            bundle_pk: StagingBundle object primary key

        Keyword Args:
            number_of_chunks: the number of page-splitting jobs to run;
                each huey-page-split-task will process approximately
                number_of_pages_in_bundle / number_of_chunks pages.
            read_after: Automatically read the qr codes from the bundle after
                upload+splitting is finished.

        Returns:
            None
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

        with transaction.atomic(durable=True):
            x = PagesToImagesHueyTask.objects.create(
                bundle=bundle_obj,
                status=PagesToImagesHueyTask.STARTING,
            )
            tracker_pk = x.pk
        res = huey_parent_split_bundle_task(
            bundle_pk,
            number_of_chunks,
            tracker_pk=tracker_pk,
            read_after=read_after,
        )
        # print(f"Just enqueued Huey parent_split_and_save task id={res.id}")
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

    @transaction.atomic
    def get_bundle_split_completions(self, bundle_pk: int) -> int:
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        return PagesToImagesHueyTask.objects.get(bundle=bundle_obj).completed_pages

    @transaction.atomic
    def is_bundle_mid_splitting(self, bundle_pk: int) -> bool:
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        if bundle_obj.has_page_images:
            return False

        query = PagesToImagesHueyTask.objects.filter(bundle=bundle_obj)
        if query.exists():  # have run a bundle-split task previously
            if query.exclude(
                status=PagesToImagesHueyTask.COMPLETE
            ).exists():  # one of these is not completed, so must be mid-run
                return True
            else:  # all have finished previously
                return False
        else:  # no such qr-reading tasks have been done
            return False

    def are_bundles_mid_splitting(self) -> dict[str, bool]:
        """Returns a dict of each staging bundle (slug) and whether it is still mid-split."""
        return {
            bundle_obj.slug: self.is_bundle_mid_splitting(bundle_obj.pk)
            for bundle_obj in StagingBundle.objects.all()
        }

    @transaction.atomic
    def remove_bundle(self, bundle_name: str, *, user: str | None = None) -> None:
        """Remove a bundle PDF from the filesystem and database.

        Args:
            bundle_name (str): which bundle.

        Keyword Args:
            user (None/str): also filter by user. TODO: user is *not* for
                permissions: looks like just a way to identify a bundle.

        Returns:
            None
        """
        # TODO - deprecate this function in place of the one that uses PK instead of name
        if user:
            bundle = StagingBundle.objects.get(
                user=user,
                slug=bundle_name,
            )
        else:
            bundle = StagingBundle.objects.get(slug=bundle_name)
        self._remove_bundle_by_pk(bundle.pk)

    def _remove_bundle_by_pk(self, bundle_pk: int) -> None:
        """Remove a bundle PDF from the filesystem + database.

        Args:
            bundle_pk: the primary key for a particular bundle.
        """
        with transaction.atomic():
            _bundle_obj = (
                StagingBundle.objects.select_for_update().filter(pk=bundle_pk).get()
            )

            if self.is_bundle_mid_splitting(_bundle_obj.pk):
                raise PlomBundleLockedException(
                    "Bundle is upload / splitting. Wait until that is finished before removing it"
                )
            if self.is_bundle_mid_qr_read(_bundle_obj.pk):
                raise PlomBundleLockedException(
                    "Bundle is mid qr read. Wait until that is finished before removing it"
                )
            # will raise exception if the bundle is locked or push-locked - cannot remove it.
            check_bundle_object_is_neither_locked_nor_pushed(_bundle_obj)
            pathlib.Path(_bundle_obj.pdf_file.path).unlink()
            _bundle_obj.delete()

    @transaction.atomic
    def check_for_duplicate_hash(self, pdf_hash: str) -> bool:
        """Check if a PDF has already been uploaded.

        Returns True if the hash already exists in the database.
        """
        return StagingBundle.objects.filter(pdf_hash=pdf_hash).exists()

    @transaction.atomic
    def get_bundle_name_from_hash(self, pdf_hash: str) -> str | None:
        """Get a bundle-name from a hash or return none."""
        try:
            return StagingBundle.objects.get(pdf_hash=pdf_hash).slug
        except ObjectDoesNotExist:
            return None

    def get_bundle_from_pk(self, pk: int) -> StagingBundle:
        """Return a StagingBundle object from its pk."""
        return StagingBundle.objects.get(pk=pk)

    @transaction.atomic
    def get_image(self, bundle_id: int, index: int) -> StagingImage:
        """Get an image from the database from bundle-id, and index."""
        bundle = self.get_bundle_from_pk(bundle_id)
        return StagingImage.objects.get(
            bundle=bundle,
            bundle_order=index,
        )

    @transaction.atomic
    def get_first_image(self, bundle_obj: StagingBundle) -> StagingImage:
        """Get the first image from the given bundle."""
        return StagingImage.objects.get(
            bundle=bundle_obj,
            bundle_order=1,
        )

    @transaction.atomic
    def get_thumbnail_image(self, bundle_pk: int, index: int) -> StagingImage:
        """Get a thubnail image from the database.

        To uniquely identify an image, we need a bundle and a page index.
        """
        bundle_obj = self.get_bundle_from_pk(bundle_pk)
        img = StagingImage.objects.get(bundle=bundle_obj, bundle_order=index)
        return img.stagingthumbnail

    @transaction.atomic
    def get_n_images(self, bundle: StagingBundle) -> int:
        """Get the number of page images in a bundle from the number of its StagingImages."""
        return bundle.stagingimage_set.count()

    @transaction.atomic
    def get_user_bundles(self, user: User) -> list[StagingBundle]:
        """Return all of the staging bundles that the given user uploaded."""
        return list(StagingBundle.objects.filter(user=user))

    @transaction.atomic
    def get_all_staging_bundles(self) -> list[StagingBundle]:
        """Return all of the staging bundles in reverse chronological order."""
        return list(StagingBundle.objects.all().order_by("-timestamp"))

    def get_most_recent_unpushed_bundle(self) -> StagingBundle | None:
        """Return all of the staging bundles in reverse chronological order."""
        return (
            StagingBundle.objects.filter(pushed=False, is_push_locked=False)
            .order_by("-timestamp")
            .first()
        )

    def staging_bundles_exist(self) -> bool:
        """Check if any staging bundles exist."""
        return StagingBundle.objects.all().exists()

    def parse_qr_code(self, list_qr_codes: list[dict[str, Any]]) -> dict[str, Any]:
        """Parse QR codes into list of dictionaries.

        Args:
            list_qr_codes: (list) QR codes returned from QRextract() method as a dictionary

        Returns:
            groupings: (dict) Set of data from raw-qr-strings
            {
                'NE': {
                    'page_type': 'plom_qr',
                    'page_info': {
                        'paper_id': 1,
                        'page_num': 3,
                        'version_num': 1,
                        'public_code': '93849',
                    }
                    'quadrant': '1',
                    'tpv': '00001003001',
                    'x_coord': 2204,
                    'y_coord': 279.5
                },
                'SW': {
                    'page_type': 'plom_qr',
                    'page_info': {
                        'paper_id': 1,
                        'page_num': 3,
                        'version_num': 1,
                        'public_code': '93849',
                }
                    'quadrant': '3',
                    'tpv': '00001003001',
                    'x_coord': 234,
                    'y_coord': 2909.5
                },
                'SE': {
                    'page_type': 'plom_qr',
                    'page_info': {
                        'paper_id': 1,
                        'page_num': 3,
                        'version_num': 1,
                        'public_code': '93849',
                    }
                    'quadrant': '4',
                    'tpv': '00001003001',
                    'x_coord': 2203,
                    'y_coord': 2906.5
                }
            }
            Alternatively, if the page is an extra page, then returns a similar dict but with entries of the form
                    'SE': {
                    'page_type': 'plom_extra',
                    'quadrant': '4',
                    'tpv': 'plomX',
                    'x_coord': 2203,
                    'y_coord': 2906.5
                }
            Similarly,, if the page is a scrap-paper page, then returns
                    'SE': {
                    'page_type': 'plom_scrap',
                    'quadrant': '4',
                    'tpv': 'plomS',
                    'x_coord': 2203,
                    'y_coord': 2906.5
                }

        """
        # ++++++++++++++++++++++
        # TODO - hack this to handle tpv and plomX pages.
        # Need to add a tpv-utils method to decide if tpv or plomX and then
        # act accordingly here.
        # ++++++++++++++++++++++

        groupings = {}
        # TODO - simplify this loop using enumerate(list) or similar.
        for page in range(len(list_qr_codes)):
            for quadrant in list_qr_codes[page]:
                # note that from legacy-scan code the tpv_signature is the full raw "TTTTTPPPVVVOCCCCC" qr-string
                # while tpv refers to "TTTTTPPPVVV"
                raw_qr_string = list_qr_codes[page][quadrant].get("tpv_signature", None)
                if raw_qr_string is None:
                    continue
                x_coord = list_qr_codes[page][quadrant].get("x")
                y_coord = list_qr_codes[page][quadrant].get("y")
                qr_code_dict = {
                    "raw_qr_string": raw_qr_string,
                    "x_coord": x_coord,
                    "y_coord": y_coord,
                }

                if isValidTPV(raw_qr_string):
                    paper_id, page_num, version_num, public_code, corner = parseTPV(
                        raw_qr_string
                    )
                    tpv = getPaperPageVersion(
                        list_qr_codes[page][quadrant].get("tpv_signature")
                    )
                    qr_code_dict.update(
                        {
                            "page_type": "plom_qr",
                            "page_info": {
                                "paper_id": paper_id,
                                "page_num": page_num,
                                "version_num": version_num,
                                "public_code": public_code,
                            },
                            "quadrant": corner,
                            "tpv": tpv,
                        }
                    )
                elif isValidExtraPageCode(raw_qr_string):
                    corner = parseExtraPageCode(raw_qr_string)
                    qr_code_dict.update(
                        {
                            "page_type": "plom_extra",
                            "quadrant": corner,
                            "tpv": "plomX",
                        }
                    )
                elif isValidScrapPaperCode(raw_qr_string):
                    corner = parseExtraPageCode(raw_qr_string)
                    qr_code_dict.update(
                        {
                            "page_type": "plom_scrap",
                            "quadrant": corner,
                            "tpv": "plomS",
                        }
                    )
                groupings[quadrant] = qr_code_dict
        return groupings

    def read_qr_codes(self, bundle_pk: int) -> None:
        """Read QR codes of scanned pages in a bundle.

        QR Code:
        -         Test ID:  00001
        -        Page Num:  00#
        -     Version Num:  00#
        -              NW:  2
        -              NE:  1
        -              SW:  3
        -              SE:  4
        - Last five digit:  93849

        Args:
            bundle_pk: primary key of bundle DB object
        """
        root_folder = settings.MEDIA_ROOT / "page_images"
        root_folder.mkdir(exist_ok=True)

        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        # check that the qr-codes have not been read already, or that a task has not been set

        if ManageParseQR.objects.filter(bundle=bundle_obj).exists():
            return

        with transaction.atomic(durable=True):
            x = ManageParseQR.objects.create(
                bundle=bundle_obj,
                status=ManageParseQR.STARTING,
            )
            tracker_pk = x.pk

        res = huey_parent_read_qr_codes_task(bundle_pk, tracker_pk=tracker_pk)
        # print(f"Just enqueued Huey parent_read_qr_codes task id={res.id}")
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

    def map_bundle_pages(
        self,
        bundle_pk: int,
        *,
        papernum: int,
        pages_to_question_indices: list[list[int]],
    ) -> None:
        """Maps an entire bundle's pages onto zero or more questions per page.

        Args:
            bundle_pk: primary key of bundle DB object.

        Keyword Args:
            papernum (int): the number of the test-paper
            pages_to_question_indices: a list same length
                as the bundle, each element is variable-length list
                of which questions (by one-based question index)
                to attach that page too.  If one of those inner
                lists is empty, it means to drop (discard) that
                particular page.

        Returns:
            None
        """
        root_folder = settings.MEDIA_ROOT / "page_images"
        root_folder.mkdir(exist_ok=True)

        bundle_obj = (
            StagingBundle.objects.filter(pk=bundle_pk).select_for_update().get()
        )

        # TODO: assert the length of question is same as pages in bundle

        with transaction.atomic():
            # TODO: how do we walk them in order?
            for page_img, qlist in zip(
                bundle_obj.stagingimage_set.all().order_by("bundle_order"),
                pages_to_question_indices,
            ):
                if not qlist:
                    page_img.image_type = StagingImage.DISCARD
                    page_img.save()
                    DiscardStagingImage.objects.create(
                        staging_image=page_img, discard_reason="map said drop this page"
                    )
                    continue
                page_img.image_type = StagingImage.EXTRA
                # TODO = update the qr-code info in the underlying image
                page_img.save()
                ExtraStagingImage.objects.create(
                    staging_image=page_img,
                    paper_number=papernum,
                    question_list=qlist,
                )
            # finally - mark the bundle as having had its qr-codes read.
            bundle_obj.has_qr_codes = True
            bundle_obj.save()

    @transaction.atomic
    def get_bundle_qr_completions(self, bundle_pk: int) -> int:
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        return ManageParseQR.objects.get(bundle=bundle_obj).completed_pages

    @transaction.atomic
    def is_bundle_mid_qr_read(self, bundle_pk: int) -> int:
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        if bundle_obj.has_qr_codes:
            return False

        query = ManageParseQR.objects.filter(bundle=bundle_obj)
        if query.exists():  # have run a qr-read task previously
            if query.exclude(
                status=ManageParseQR.COMPLETE
            ).exists():  # one of these is not completed, so must be mid-run
                return True
            else:  # all have finished previously
                return False
        else:  # no such qr-reading tasks have been done
            return False

    def are_bundles_mid_qr_read(self) -> dict[str, bool]:
        """Returns a dict of each staging bundle (slug) and whether it is still mid-qr-read."""
        return {
            bundle_obj.slug: self.is_bundle_mid_qr_read(bundle_obj.pk)
            for bundle_obj in StagingBundle.objects.all()
        }

    @transaction.atomic
    def get_qr_code_results(
        self, bundle: StagingBundle, page_index: int
    ) -> dict[str, Any] | None:
        """Check the results of a QR code scanning task.

        If done, return the QR code data. Otherwise, return None.
        """
        return StagingImage.objects.get(
            bundle=bundle, bundle_order=page_index
        ).parsed_qr

    @transaction.atomic
    def get_all_known_images(self, bundle: StagingBundle) -> list[StagingImage]:
        """Get all the images with completed QR code data - they can be pushed."""
        return list(bundle.stagingimage_set.filter(image_type=StagingImage.KNOWN))

    @transaction.atomic
    def get_n_known_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.KNOWN).count()

    @transaction.atomic
    def get_n_unknown_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.UNKNOWN).count()

    @transaction.atomic
    def get_n_extra_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.EXTRA).count()

    @transaction.atomic
    def get_n_extra_images_with_data(self, bundle: StagingBundle) -> int:
        # note - we must check that we have set both questions and pages
        return bundle.stagingimage_set.filter(
            image_type=StagingImage.EXTRA,
            extrastagingimage__paper_number__isnull=False,
            extrastagingimage__question_list__isnull=False,
        ).count()

    @transaction.atomic
    def do_all_extra_images_have_data(self, bundle: StagingBundle) -> int:
        # Make sure all question pages have both paper-number and question-lists
        epages = bundle.stagingimage_set.filter(image_type=StagingImage.EXTRA)
        return not epages.filter(
            Q(extrastagingimage__paper_number__isnull=True)
            | Q(extrastagingimage__question_list__isnull=True)
        ).exists()
        # if you can find an extra page with a null paper_number, or one with a null question-list then it is not ready.

    @transaction.atomic
    def get_n_error_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.ERROR).count()

    @transaction.atomic
    def get_n_discard_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.DISCARD).count()

    @transaction.atomic
    def staging_bundle_status_cmd(
        self,
    ) -> list[tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any]]:
        bundles = StagingBundle.objects.all().order_by("slug")

        bundle_status = []
        status_header = (
            "Bundle name",
            "Id",
            "Total Pages",
            "Unknowns",
            "Knowns",
            "Extra (w data)",
            "Discards",
            "Error",
            "QR read",
            "Pushed",
            "Uploaded by",
        )
        bundle_status.append(status_header)
        for bundle in bundles:
            images = StagingImage.objects.filter(bundle=bundle)
            n_unknowns = self.get_n_unknown_images(bundle)
            n_knowns = self.get_n_known_images(bundle)
            n_extras_w_data = self.get_n_extra_images_with_data(bundle)
            n_discards = self.get_n_discard_images(bundle)
            n_errors = self.get_n_error_images(bundle)

            if self.is_bundle_mid_splitting(bundle.pk):
                count = PagesToImagesHueyTask.objects.get(bundle=bundle).completed_pages
                total_pages = f"in progress: {count} of {bundle.number_of_pages}"
            else:
                total_pages = images.count()

            bundle_qr_read = bundle.has_qr_codes
            if self.is_bundle_mid_qr_read(bundle.pk):
                count = ManageParseQR.objects.get(bundle=bundle).completed_pages
                bundle_qr_read = f"in progress ({count})"

            bundle_data = (
                bundle.slug,
                bundle.pk,
                total_pages,
                n_unknowns,
                n_knowns,
                n_extras_w_data,
                n_discards,
                n_errors,
                bundle_qr_read,
                bundle.pushed,
                bundle.user.username,
            )
            bundle_status.append(bundle_data)
        return bundle_status

    def read_bundle_qr_cmd(self, bundle_name: str) -> None:
        """Read all the QR codes from a bundle specified by its name."""
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        if not bundle_obj.has_page_images:
            raise ValueError(f"Please wait for {bundle_name} to upload...")
        elif bundle_obj.has_qr_codes:
            raise ValueError(f"QR codes for {bundle_name} has been read.")
        self.read_qr_codes(bundle_obj.pk)

    @transaction.atomic
    def map_bundle_pages_cmd(
        self,
        bundle_name: str,
        *,
        papernum: int,
        question_map: str | list[int] | list[list[int]],
    ) -> None:
        """Maps an entire bundle's pages onto zero or more questions per page.

        Args:
            bundle_name: which bundle.

        Keyword Args:
            papernum: which paper.
            question_map: specifies how pages of this bundle should be mapped
                onto questions.  In principle it can be many different things,
                although the current single caller passes only strings.
                You can pass a single integer, or a list like `[1,2,3]`
                which updates each page to questions 1, 2 and 3.
                You can also pass the special string `all` which uploads
                each page to all questions.
                If you need to specify questions per page, you can pass a list
                of lists: each list gives the questions for each page.
                For example, `[[1],[2],[2],[2],[3]]` would upload page 1 to
                question 1, pages 2-4 to question 2 and page 5 to question 3.
                A common case is `-q [[1],[2],[3]]` to upload one page per
                question.
                An empty list will "discard" that particular page.

        Returns:
            None.

        This is the command "front-end" to :method:`map_bundle_pages`,
        see also docs there.
        """
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist as e:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!") from e

        if not bundle_obj.has_page_images:
            raise ValueError(f"Please wait for {bundle_name} to upload...")
        # elif bundle_obj.has_qr_codes:
        #    raise ValueError(f"QR codes for {bundle_name} has been read.")
        # TODO: ensure papernum exists, here or in the none-cmd?

        numpages = bundle_obj.number_of_pages
        numquestions = SpecificationService.get_n_questions()
        mymap = canonicalize_page_question_map(question_map, numpages, numquestions)
        self.map_bundle_pages(
            bundle_obj.pk, papernum=papernum, pages_to_question_indices=mymap
        )

    @transaction.atomic
    def is_bundle_perfect(self, bundle_pk: int) -> bool:
        """Tests if the bundle (given by its pk) is perfect.

        A bundle is perfect when
          * no unread pages, no error-pages, no unknown-pages, and
          * all extra pages have data.
        this, in turn, means that all pages present in bundle are
          * known or discard, or
          * are extra-pages with data
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        # a bundle is perfect if it has

        # check for unread, unknown, error pages
        if bundle_obj.stagingimage_set.filter(
            image_type__in=[
                StagingImage.UNKNOWN,
                StagingImage.UNREAD,
                StagingImage.ERROR,
            ]
        ).exists():
            return False
        # check for extra pages without data
        epages = bundle_obj.stagingimage_set.filter(image_type=StagingImage.EXTRA)
        if epages.filter(
            Q(extrastagingimage__paper_number__isnull=True)
            | Q(extrastagingimage__question_list__isnull=True)
        ).exists():
            return False

        return True

    def are_bundles_perfect(self) -> dict[str, bool]:
        """Returns a dict of each staging bundle (slug) and whether it is perfect."""
        return {
            bundle_obj.slug: self.is_bundle_perfect(bundle_obj.pk)
            for bundle_obj in StagingBundle.objects.all()
        }

    def are_bundles_pushed(self) -> dict[str, bool]:
        """Returns a dict of each staging bundle (slug) and whether it is pushed."""
        return {
            bundle_obj.slug: bundle_obj.pushed
            for bundle_obj in StagingBundle.objects.all()
        }

    @transaction.atomic
    def get_bundle_push_lock_information(
        self, include_pushed: bool = False
    ) -> list[tuple[Any, Any, Any]]:
        info = [("name", "push-locked", "pushed")]
        if include_pushed:
            for bundle_obj in StagingBundle.objects.all().order_by("slug"):
                info.append(
                    (bundle_obj.slug, bundle_obj.is_push_locked, bundle_obj.pushed)
                )
        else:
            for bundle_obj in StagingBundle.objects.filter(pushed=False).order_by(
                "slug"
            ):
                info.append(
                    (bundle_obj.slug, bundle_obj.is_push_locked, bundle_obj.pushed)
                )

        return info

    def push_lock_bundle_cmd(self, bundle_name: str) -> None:
        with transaction.atomic():
            try:
                bundle_obj = (
                    StagingBundle.objects.select_for_update()
                    .filter(slug=bundle_name)
                    .get()
                )
            except ObjectDoesNotExist:
                raise ValueError(f"Bundle '{bundle_name}' does not exist!")

            if bundle_obj.pushed:
                raise ValueError(
                    f"Bundle '{bundle_name}' has been pushed. Cannot modify."
                )

            if bundle_obj.is_push_locked:
                raise PlomBundleLockedException(
                    f"Bundle '{bundle_name}' is already push-locked."
                )

            bundle_obj.is_push_locked = True
            bundle_obj.save()

    def push_unlock_bundle_cmd(self, bundle_name: str) -> None:
        with transaction.atomic():
            try:
                bundle_obj = (
                    StagingBundle.objects.select_for_update()
                    .filter(slug=bundle_name)
                    .get()
                )
            except ObjectDoesNotExist:
                raise ValueError(f"Bundle '{bundle_name}' does not exist!")

            if bundle_obj.pushed:
                raise ValueError(
                    f"Bundle '{bundle_name}' has been pushed. Cannot modify."
                )

            if not bundle_obj.is_push_locked:
                raise ValueError(
                    f"Bundle '{bundle_name}' is not push-locked. No unlock required."
                )
            bundle_obj.is_push_locked = False
            bundle_obj.save()

    @transaction.atomic
    def toggle_bundle_push_lock(self, bundle_pk: int) -> None:
        bundle_obj = (
            StagingBundle.objects.select_for_update().filter(pk=bundle_pk).get()
        )
        bundle_obj.is_push_locked = not (bundle_obj.is_push_locked)
        bundle_obj.save()

    def push_bundle_to_server(self, bundle_obj_pk: int, user_obj: User) -> None:
        """Push a legal bundle from staging to the core server.

        Args:
            bundle_obj_pk: The pk of the stagingBundle object to be pushed to the core server
            user_obj: The (django) User object that is doing the pushing

        Returns:
            None

        Exceptions:
            ValueError: When the bundle is currently being pushed
            ValueError: When the bundle has already been pushed,
            ValueError: When the qr codes have not all been read,
            ValueError: When the bundle is not prefect (eg still has errors or unknowns),
            RuntimeError: When something very strange happens!!
            PlomPushCollisionException: When images in the bundle collide with existing pushed images
            PlomBundleLockedException: When any bundle is push-locked, or the current one is locked/push-locked.
        """
        # raises exception if *any* bundle is push-locked
        # (only allow one bundle at a time to be pushed.)
        check_any_bundle_push_locked()

        # now try to grab the bundle to set lock and check stuff
        with transaction.atomic():
            bundle_obj = (
                StagingBundle.objects.select_for_update().filter(pk=bundle_obj_pk).get()
            )

            if bundle_obj.is_push_locked:
                raise ValueError(
                    "Bundle is currently push-locked. Please wait for that process to finish"
                )
            if bundle_obj.pushed:
                raise ValueError("Bundle has already been pushed. Cannot push again.")

            if not bundle_obj.has_page_images:
                raise ValueError(
                    "Bundle has no page-images yet. Please wait for the upload process to finish."
                )
            if not bundle_obj.has_qr_codes:
                raise ValueError("QR codes are not all read - cannot push bundle.")

            # make sure bundle is "perfect"
            # note function takes a bundle-pk as argument
            if not self.is_bundle_perfect(bundle_obj.pk):
                raise ValueError("The bundle is imperfect, cannot push.")
            # the bundle is valid so we can push it --- set the lock.
            bundle_obj.is_push_locked = True
            bundle_obj.save()
            # must make sure we unlock the bundle when we are done

        # the bundle is valid so we can push it.

        raise_this_after: Any = None
        try:
            with transaction.atomic(durable=True):
                bundle_obj = (
                    StagingBundle.objects.select_for_update()
                    .filter(pk=bundle_obj_pk)
                    .get()
                )
                # This call can be slow.
                ImageBundleService().upload_valid_bundle(bundle_obj, user_obj)
                # now update the bundle and its images to say "pushed"
                bundle_obj.stagingimage_set.update(pushed=True)
                bundle_obj.pushed = True
                bundle_obj.save()
        except PlomPushCollisionException as err:
            raise_this_after = err
        except RuntimeError as err:
            # This should only be for **very bad** errors
            raise_this_after = err
        finally:
            # unlock the bundle when we are done
            with transaction.atomic():
                bundle_obj = (
                    StagingBundle.objects.filter(pk=bundle_obj_pk)
                    .select_for_update()
                    .get()
                )
                bundle_obj.is_push_locked = False
                bundle_obj.save()

        # and now after the bundle-lock is done, raise exception that occurred
        if raise_this_after:
            raise raise_this_after

    def push_bundle_cmd(self, bundle_name: str, username: str) -> None:
        """Wrapper around push_bundle_to_server().

        Args:
            bundle_name: The name of the staging bundle to be pushed
            username: The name of the user doing the pushing

        Returns:
            None

        Exceptions:
            ValueError: When the bundle does not exist
            ValueError: When the user does not exist or has wrong permissions
        """
        try:
            bundle_obj_pk = StagingBundle.objects.get(slug=bundle_name).pk
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")

        # username => user_object, if in scanner group, else exception raised.
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="scanner"
            )
        except ObjectDoesNotExist:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        self.push_bundle_to_server(bundle_obj_pk, user_obj)

    @transaction.atomic
    def get_bundle_pages_info_list(
        self, bundle_obj: StagingBundle
    ) -> list[dict[str, Any]]:
        """List of info about the pages in a bundle in bundle order.

        Args:
            bundle_obj (todo): the pk reference to a bundle.

        Returns:
            list: the pages within the given bundle ordered by their
            bundle-order.  Each item in the list is a dict with keys
            ``status`` (the image type), ``order``, ``rotation``,
            and ``info``.
            The latter value is itself a dict containing different
            items depending on the image-type.  For error-pages and
            discard-pages, it contains the ``reason`` while for
            known-pages it contains ``paper_number``, ``page_number``
            and ``version``.  Finally for extra-pages, it contains
            ``paper_number``, and ``question_list``.
        """
        # compute number of digits in longest page number to pad the page numbering
        n_digits = len(str(bundle_obj.number_of_pages))

        # We compute the list in two steps.
        # First we compute a dict of (key, value) (bundle_order, page_information)
        # Second we flatten that dict into an ordered list.

        # To do build the dict, we loop over all images and set up the
        # dict entries, and then loop over each separate image-type in
        # order to populate the information-field. This allows us to
        # prefetch the required information and so avoid any N+1 query
        # problems.
        pages = {}
        for img in bundle_obj.stagingimage_set.all().order_by("bundle_order"):
            pages[img.bundle_order] = {
                "status": img.image_type.lower(),
                "info": {},
                # order is 1-indexed
                "order": f"{img.bundle_order}".zfill(n_digits),
                "rotation": img.rotation,
                "n_qr_read": len(img.parsed_qr),
            }

        for img in bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.ERROR
        ).prefetch_related("errorstagingimage"):
            pages[img.bundle_order]["info"] = {
                "reason": img.errorstagingimage.error_reason
            }

        for img in bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.DISCARD
        ).prefetch_related("discardstagingimage"):
            pages[img.bundle_order]["info"] = {
                "reason": img.discardstagingimage.discard_reason
            }

        for img in bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.KNOWN
        ).prefetch_related("knownstagingimage"):
            pages[img.bundle_order]["info"] = {
                "paper_number": img.knownstagingimage.paper_number,
                "page_number": img.knownstagingimage.page_number,
                "version": img.knownstagingimage.version,
            }
        for img in bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.EXTRA
        ).prefetch_related("extrastagingimage"):
            pages[img.bundle_order]["info"] = {
                "paper_number": img.extrastagingimage.paper_number,
                "question_list": img.extrastagingimage.question_list,
            }

        # now build an ordered list by running the keys (which are bundle-order) of the pages-dict in order.
        return [pages[ord] for ord in sorted(pages.keys())]

    @transaction.atomic
    def get_bundle_papers_pages_list(
        self, bundle_obj: StagingBundle
    ) -> list[tuple[int, list[dict[str, Any]]]]:
        """Return an ordered list of papers and their known/extra pages in the given bundle.

        Each item in the list is a pair
        (paper_number, page-info). The page-info is itself a ordered
        list of dicts. Each dict contains information about a page in
        the given paper in the given bundle.
        """
        # We build the ordered list in two steps. First build a dict of lists indexed by paper-number.
        papers: dict[int, list[dict[str, Any]]] = {}
        # Loop over the known-images first and then the extra-pages.
        for known in (
            KnownStagingImage.objects.filter(staging_image__bundle=bundle_obj)
            .order_by("paper_number", "page_number")
            .prefetch_related("staging_image")
        ):
            papers.setdefault(known.paper_number, []).append(
                {
                    "type": "known",
                    "page": known.page_number,
                    "order": known.staging_image.bundle_order,
                }
            )
        # Now loop over the extra pages
        for extra in (
            ExtraStagingImage.objects.filter(staging_image__bundle=bundle_obj)
            .order_by("paper_number", "question_list")
            .prefetch_related("staging_image")
        ):
            # we can skip those without data
            if extra.paper_number and extra.question_list:
                papers.setdefault(extra.paper_number, []).append(
                    {
                        "type": "extra",
                        "question_list": extra.question_list,
                        "order": extra.staging_image.bundle_order,
                    }
                )
        # # recast paper_pages as an **ordered** list of tuples (paper, page-info)
        return [
            (paper_number, page_info)
            for paper_number, page_info in sorted(papers.items())
        ]

    @transaction.atomic
    def get_bundle_pages_info_cmd(
        self, bundle_name: str
    ) -> list[tuple[int, dict[str, Any]]]:
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")
        return self.get_bundle_pages_info_list(bundle_obj)

    @transaction.atomic
    def get_bundle_extra_pages_info(
        self, bundle_obj: StagingBundle
    ) -> dict[int, dict[str, Any]]:
        # compute number of digits in longest page number to pad the page numbering
        n_digits = len(str(bundle_obj.number_of_pages))

        pages = {}
        for img in bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.EXTRA
        ).all():
            pages[img.bundle_order] = {
                "status": img.image_type,
                "info": {
                    "paper_number": img.extrastagingimage.paper_number,
                    "question_list": img.extrastagingimage.question_list,
                },
                "order": f"{img.bundle_order}".zfill(n_digits),
                "rotation": img.rotation,
            }
        return pages

    @transaction.atomic
    def get_bundle_extra_pages_info_cmd(
        self, bundle_name: str
    ) -> dict[int, dict[str, Any]]:
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")
        return self.get_bundle_extra_pages_info(bundle_obj)

    @transaction.atomic
    def get_bundle_single_page_info(
        self, bundle_obj: StagingBundle, index: int
    ) -> dict[str, Any]:
        # compute number of digits in longest page number to pad the page numbering
        n_digits = len(str(bundle_obj.number_of_pages))

        img = bundle_obj.stagingimage_set.get(bundle_order=index)
        current_page = {
            "status": img.image_type.lower(),
            # order is 1-indexed
            "order": f"{img.bundle_order}".zfill(n_digits),
            "rotation": img.rotation,
            "qr_codes": img.parsed_qr,
        }
        if img.image_type == StagingImage.ERROR:
            info = {"reason": img.errorstagingimage.error_reason}
        elif img.image_type == StagingImage.DISCARD:
            info = {"reason": img.discardstagingimage.discard_reason}
        elif img.image_type == StagingImage.KNOWN:
            info = {
                "paper_number": img.knownstagingimage.paper_number,
                "page_number": img.knownstagingimage.page_number,
                "version": img.knownstagingimage.version,
            }
        elif img.image_type == StagingImage.EXTRA:
            _render = SpecificationService.render_html_flat_question_label_list
            info = {
                "paper_number": img.extrastagingimage.paper_number,
                "question_index_list": img.extrastagingimage.question_list,
                "question_list_html": _render(img.extrastagingimage.question_list),
            }
        else:
            info = {}

        current_page.update({"info": info})
        return current_page

    @transaction.atomic
    def get_bundle_paper_numbers(self, bundle_obj: StagingBundle) -> list[int]:
        """Return a sorted list of paper-numbers in the given bundle as determined by known and extra pages."""
        paper_list = []
        for img in bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.KNOWN
        ).prefetch_related("knownstagingimage"):
            paper_list.append(img.knownstagingimage.paper_number)

        for img in bundle_obj.stagingimage_set.filter(
            image_type=StagingImage.EXTRA
        ).prefetch_related("extrastagingimage"):
            if (
                img.extrastagingimage.paper_number
                and img.extrastagingimage.question_list
            ):
                paper_list.append(img.extrastagingimage.paper_number)
        return sorted(list(set(paper_list)))

    @transaction.atomic
    def get_bundle_paper_numbers_cmd(self, bundle_name: str) -> list[int]:
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")
        return self.get_bundle_paper_numbers(bundle_obj)

    @transaction.atomic
    def get_bundle_missing_paper_page_numbers(
        self, bundle_obj: StagingBundle
    ) -> list[tuple[int, list[int]]]:
        """Return a list of the missing known pages in papers in the given bundle.

        Args:
            bundle_obj: the given staging bundle to check.

        Returns:
            A list of pairs `(paper_number (int), [missing pages (int)])`.
        """
        n_pages = SpecificationService.get_n_pages()
        papers_pages: dict[int, list] = {}
        # get all known images in the bundle
        # put in dict as {paper_number: [list of known pages present] }
        for img in StagingImage.objects.filter(
            bundle=bundle_obj, image_type=StagingImage.KNOWN
        ).prefetch_related("knownstagingimage"):
            papers_pages.setdefault(img.knownstagingimage.paper_number, [])
            papers_pages[img.knownstagingimage.paper_number].append(
                img.knownstagingimage.page_number
            )

        incomplete_papers = []
        for paper_number, page_list in sorted(papers_pages.items()):
            if len(page_list) == 0 or len(page_list) == n_pages:
                continue
            incomplete_papers.append(
                (
                    paper_number,
                    [pg for pg in range(1, n_pages + 1) if pg not in page_list],
                )
            )
        return incomplete_papers

    @transaction.atomic
    def get_bundle_number_incomplete_papers(self, bundle_obj: StagingBundle) -> int:
        """Return number of incomplete papers in the given bundle.

        A paper is incomplete when it has more than zero but not all its known pages.

        Args:
            bundle_obj: the given staging bundle to check.

        Returns:
            The number of incomplete papers in the bundle.
        """
        n_pages = SpecificationService.get_n_pages()
        papers_pages: dict[int, int] = {}
        # get all known images in the bundle
        # put in dict as {page_number: number of known pages present] }
        for img in StagingImage.objects.filter(
            bundle=bundle_obj, image_type=StagingImage.KNOWN
        ).prefetch_related("knownstagingimage"):
            papers_pages.setdefault(img.knownstagingimage.paper_number, 0)
            papers_pages[img.knownstagingimage.paper_number] += 1

        number_incomplete = 0
        for paper_number, page_count in sorted(papers_pages.items()):
            if page_count > 0 and page_count < n_pages:
                number_incomplete += 1

        return number_incomplete

    @transaction.atomic
    def get_bundle_missing_paper_page_numbers_cmd(
        self, bundle_name: str
    ) -> list[tuple[int, list[int]]]:
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")
        return self.get_bundle_missing_paper_page_numbers(bundle_obj)

    @transaction.atomic
    def get_bundle_unknown_pages_info(
        self, bundle_obj: StagingBundle
    ) -> list[dict[str, Any]]:
        # compute number of digits in longest page number to pad the page numbering
        n_digits = len(str(bundle_obj.number_of_pages))

        pages = []
        for img in (
            bundle_obj.stagingimage_set.filter(image_type=StagingImage.UNKNOWN)
            .all()
            .order_by("bundle_order")
        ):
            pages.append(
                {
                    "status": img.image_type,
                    "order": f"{img.bundle_order}".zfill(n_digits),
                    "rotation": img.rotation,
                }
            )
        return pages

    @transaction.atomic
    def get_bundle_unknown_pages_info_cmd(
        self, bundle_name: str
    ) -> list[dict[str, Any]]:
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")
        return self.get_bundle_unknown_pages_info(bundle_obj)

    @transaction.atomic
    def get_bundle_discard_pages_info(
        self, bundle_obj: StagingBundle
    ) -> list[dict[str, Any]]:
        # compute number of digits in longest page number to pad the page numbering
        n_digits = len(str(bundle_obj.number_of_pages))

        pages = []
        for img in (
            bundle_obj.stagingimage_set.filter(image_type=StagingImage.DISCARD)
            .prefetch_related("discardstagingimage")
            .all()
            .order_by("bundle_order")
        ):
            pages.append(
                {
                    "status": img.image_type,
                    "order": f"{img.bundle_order}".zfill(n_digits),
                    "rotation": img.rotation,
                    "reason": img.discardstagingimage.discard_reason,
                }
            )
        return pages

    @transaction.atomic
    def get_bundle_discard_pages_info_cmd(
        self, bundle_name: str
    ) -> list[dict[str, Any]]:
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")
        return self.get_bundle_discard_pages_info(bundle_obj)

    def get_bundle_colliding_images(self, bundle_obj: StagingBundle) -> list[int]:
        """Return a list of orders ("pages") in this bundle that collide with something that has been pushed."""
        # if it has been pushed then no collisions
        if bundle_obj.pushed:
            return []

        # look at each known-image and see if it corresponds to a
        # paper/page that already has an image
        colliding_images = []
        for img in (
            bundle_obj.stagingimage_set.filter(image_type=StagingImage.KNOWN)
            .prefetch_related("knownstagingimage")
            .order_by("bundle_order")
        ):
            known = img.knownstagingimage
            if Image.objects.filter(
                fixedpage__paper__paper_number=known.paper_number,
                fixedpage__page_number=known.page_number,
            ).exists():
                colliding_images.append(img.bundle_order)
        return sorted(colliding_images)


# ----------------------------------------
# factor out the huey tasks.
# ----------------------------------------


# The decorated function returns a ``huey.api.Result``
@db_task(queue="parentchores", context=True)
def huey_parent_split_bundle_task(
    bundle_pk: int,
    number_of_chunks: int,
    *,
    tracker_pk: int,
    read_after: bool = False,
    # TODO - CBM - what type should task have?
    task=None,
) -> bool:
    """Split a PDF document into individual page images.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        bundle_pk: StagingBundle object primary key
        number_of_chunks: the number of page-splitting jobs to run;
            each huey-page-split-task will handle 1/number_of_chunks of the
            pages in the bundle.

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        read_after: automatically trigger a qr-code read after splitting finished.
        task: includes our ID in the Huey process queue.

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".
    """
    from time import sleep, time

    start_time = time()
    bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

    HueyTaskTracker.transition_to_running(tracker_pk, task.id)

    # cut the list of all indices into chunks
    bundle_length = bundle_obj.number_of_pages
    assert bundle_length is not None
    chunk_length = ceil(bundle_length / number_of_chunks)
    # be careful with 0/1 indexing here.
    # pymupdf (which we use to process pdfs) 0-indexes pages within
    # a pdf while we 1-index bundle-positions. So at some point
    # in our code we need to add/subtract one to translate between
    # these. We add one here to make sure "order" is 1-indexed.
    all_bundle_orders = [ord + 1 for ord in range(bundle_length)]
    order_chunks = [
        all_bundle_orders[ord : ord + chunk_length]
        for ord in range(0, bundle_length, chunk_length)
    ]

    # note that we index bundle images from zero,
    with tempfile.TemporaryDirectory() as tmpdir:
        task_list = [
            huey_child_get_page_images(
                bundle_pk,
                ord_chnk,  # note pg is 1-indexed
                pathlib.Path(tmpdir),
            )
            for ord_chnk in order_chunks
        ]

        # results = [X.get(blocking=True) for X in task_list]
        n_tasks = len(task_list)
        while True:
            # list items are None (if not completed) or list [dict of page info]
            result_chunks = [X.get() for X in task_list]
            # remove all the nones to get list of completed tasks
            not_none_result_chunks = [
                chunk for chunk in result_chunks if chunk is not None
            ]
            completed_tasks = len(not_none_result_chunks)
            # flatten that list of lists to get a list of rendered pages
            results = [X for chunk in not_none_result_chunks for X in chunk]
            rendered_page_count = len(results)

            # TODO - check for error status here.

            with transaction.atomic():
                _task = PagesToImagesHueyTask.objects.select_for_update().get(
                    bundle=bundle_obj
                )
                _task.completed_pages = rendered_page_count
                _task.save()

            if completed_tasks == n_tasks:
                break
            else:
                sleep(1)

        with transaction.atomic():
            for X in results:
                with open(X["file_path"], "rb") as fh:
                    img = StagingImage.objects.create(
                        bundle=bundle_obj,
                        bundle_order=X["order"],
                        image_file=File(fh, name=X["file_name"]),
                        image_hash=X["image_hash"],
                    )
                with open(X["thumb_path"], "rb") as fh:
                    StagingThumbnail.objects.create(
                        staging_image=img, image_file=File(fh, X["thumb_name"])
                    )

            # get a new reference for updating the bundle itself
            _write_bundle = StagingBundle.objects.select_for_update().get(pk=bundle_pk)
            _write_bundle.has_page_images = True
            _write_bundle.time_to_make_page_images = time() - start_time
            _write_bundle.save()

    HueyTaskTracker.transition_to_complete(tracker_pk)
    # if requested automatically queue qr-code reading
    if read_after:
        ScanService().read_qr_codes(bundle_pk)
    return True


# The decorated function returns a ``huey.api.Result``
@db_task(queue="parentchores", context=True)
def huey_parent_read_qr_codes_task(
    bundle_pk: int,
    *,
    tracker_pk: int,
    # TODO - CBM - what type should task have?
    task=None,
) -> bool:
    """Read the QR codes of a bunch of pages.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        bundle_pk: StagingBundle object primary key

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".
    """
    from time import sleep, time

    start_time = time()

    HueyTaskTracker.transition_to_running(tracker_pk, task.id)

    bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

    task_list = [
        huey_child_parse_qr_code(page.pk) for page in bundle_obj.stagingimage_set.all()
    ]

    # results = [X.get(blocking=True) for X in task_list]

    n_tasks = len(task_list)
    while True:
        results = [X.get() for X in task_list]
        count = sum(1 for X in results if X is not None)

        with transaction.atomic():
            _task = ManageParseQR.objects.select_for_update().get(bundle=bundle_obj)
            _task.completed_pages = count
            _task.save()

        if count == n_tasks:
            break
        else:
            sleep(1)

    with transaction.atomic():
        for X in results:
            # TODO - check for error status here.
            img = StagingImage.objects.select_for_update().get(pk=X["image_pk"])
            img.parsed_qr = X["parsed_qr"]
            img.rotation = X["rotation"]
            img.save()
            # the thumbnail may need rotation.
            if img.rotation:
                update_thumbnail_after_rotation(img, img.rotation)

        # get a new reference for updating the bundle itself
        _write_bundle = StagingBundle.objects.select_for_update().get(pk=bundle_pk)
        _write_bundle.has_qr_codes = True
        _write_bundle.time_to_read_qr = time() - start_time
        _write_bundle.save()

    bundle_obj.refresh_from_db()
    QRErrorService().check_read_qr_codes(bundle_obj)

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True


# The decorated function returns a ``huey.api.Result``
@db_task(queue="tasks")
def huey_child_get_page_images(
    bundle_pk: int,
    order_list: list[int],
    basedir: pathlib.Path,
) -> list[dict[str, Any]]:
    """Render page images and save to disk in the background.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        bundle_pk: bundle DB object's primary key
        order_list: a list of bundle orders of pages to extract - 1-indexed
        basedir (pathlib.Path): were to put the image

    Returns:
        Information about the page image, including its file name,
        thumbnail, hash etc.
    """
    import pymupdf as fitz
    from plom.scan import rotate
    from PIL import Image

    bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

    rendered_page_info = []

    with fitz.open(bundle_obj.pdf_file.path) as pdf_doc:
        for order in order_list:
            basename = f"page{order:05}"
            if bundle_obj.force_page_render:
                save_path = None
                msgs = ["Force render"]
            else:
                save_path, msgs = try_to_extract_image(
                    pdf_doc[order - 1],  # PyMuPDF is 0-indexed
                    pdf_doc,
                    basedir,
                    basename,
                    bundle_obj.pdf_file,
                    do_not_extract=False,
                    add_metadata=True,
                )
            if save_path is None:
                # log.info(f"{basename}: Fitz render. No extract b/c: " + "; ".join(msgs))
                # TODO: log and consider storing in the StagingImage as well
                save_path = render_page_to_bitmap(
                    pdf_doc[order - 1],  # PyMuPDF is 0-indexed
                    basedir,
                    basename,
                    bundle_obj.pdf_file,
                    add_metadata=True,
                )

            with open(save_path, "rb") as f:
                image_hash = hashlib.sha256(f.read()).hexdigest()

            # make sure we load with exif rotations if required
            pil_img = rotate.pil_load_with_jpeg_exif_rot_applied(save_path)
            size = 256, 256
            try:
                _lanczos = Image.Resampling.LANCZOS
            except AttributeError:
                # TODO: Issue #2886: Deprecated, drop when minimum Pillow > 9.1.0
                _lanczos = Image.LANCZOS  # type: ignore
            pil_img.thumbnail(size, _lanczos)
            thumb_path = basedir / ("thumb-" + basename + ".png")
            pil_img.save(thumb_path)

            rendered_page_info.append(
                {
                    "order": order,
                    "file_name": save_path.name,
                    "file_path": str(save_path),
                    "image_hash": image_hash,
                    "thumb_name": thumb_path.name,
                    "thumb_path": str(thumb_path),
                }
            )

    # TODO - return an error of some sort here if problems?
    return rendered_page_info


# The decorated function returns a ``huey.api.Result``
@db_task(queue="tasks")
def huey_child_parse_qr_code(image_pk: int) -> dict[str, Any]:
    """Huey task to parse QR codes, check QR errors, and save to database in the background.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        image_pk: primary key of the image

    Returns:
        Information about the QR codes.
    """
    img = StagingImage.objects.get(pk=image_pk)
    image_path = img.image_file.path

    scanner = ScanService()

    code_dict = QRextract(image_path)
    page_data = scanner.parse_qr_code([code_dict])

    pipr = PageImageProcessor()

    rotation = pipr.get_rotation_angle_or_None_from_QRs(page_data)

    # Andrew wanted to leave the possibility of re-introducing hard
    # rotations in the future, such as `plom.scan.rotate_bitmap`.

    # Re-read QR codes if the page image needs to be rotated
    if rotation and rotation != 0:
        code_dict = QRextract(image_path, rotation=rotation)
        page_data = scanner.parse_qr_code([code_dict])
        # qr_error_checker.check_qr_codes(page_data, image_path, bundle)

    # Return the parsed QR codes for parent process to store in db
    return {
        "image_pk": image_pk,
        "parsed_qr": page_data,
        "rotation": rotation,
    }

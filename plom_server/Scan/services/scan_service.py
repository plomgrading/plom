# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Forest Kobayashi
# Copyright (C) 2025-2026 Aidan Murphy
# Copyright (C) 2025 Philip D. Loewen
# Copyright (C) 2025 Deep Shah

import hashlib
import logging
import pathlib
import random
import tempfile
import time
from datetime import datetime
from io import BytesIO
from math import ceil
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import QuerySet
from django.forms import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from django_huey import db_task
import huey
import huey.api
import huey.exceptions
import pymupdf

from plom.plom_exceptions import PlomConflict
from plom.scan import QRextract
from plom.scan import render_page_to_bitmap, try_to_extract_image
from plom.tpv_utils import (
    parseTPV,
    parseExtraPageCode,
    getPaperPageVersion,
    isValidTPV,
    isValidExtraPageCode,
    isValidScrapPaperCode,
    isValidBundleSeparatorPaperCode,
)

from plom_server.Papers.services import ImageBundleService, SpecificationService
from plom_server.Papers.models import MobilePage
from plom_server.Scan.services.cast_service import ScanCastService
from plom_server.Base.models import HueyTaskTracker, BaseImage
from ..models import (
    StagingBundle,
    StagingImage,
    StagingThumbnail,
    PagesToImagesChore,
    ManageParseQRChore,
)
from .qr_service import QRService
from .image_process import PageImageProcessor
from ..services.util import (
    update_thumbnail_after_rotation,
    check_any_bundle_push_locked,
    check_bundle_object_is_neither_locked_nor_pushed,
)
from plom.plom_exceptions import PlomBundleLockedException, PlomPushCollisionException


# future translation support
def _(x: str) -> str:
    return x


log = logging.getLogger(__name__)


def random_chars(n: int) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choices(alphabet, k=n))


def uniquify_str_against_list(s: str, lst_of_strs: list[str]) -> str:
    ss = s
    while ss in lst_of_strs:
        ss = s + "_" + random_chars(6)
    return ss


class ScanService:
    """Functions for staging scanned test-papers."""

    @classmethod
    def upload_bundle(
        cls,
        _uploaded_pdf_file: File,
        user: User,
        *,
        slug: str = "",
        pdf_hash: str = "",
        force_render: bool = False,
        read_after: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Upload a bundle PDF and store it in the filesystem + database.

        Also, trigger a background job to split PDF into page images and
        store in filesystem and database.  Because that is a background
        job, if it fails for any reason, the StagingBundle is still
        created.

        Note: this does not check if the user has appropriate permissions.
        You either need to do that yourself or consider calling
        :meth:`upload_bundle_cmd`_ instead.

        Args:
            _uploaded_pdf_file (Django File): File-object containing the pdf
                (can also be a TemporaryUploadedFile or InMemoryUploadedFile).
            user (Django User): the user uploading the file

        Keyword Args:
            pdf_hash: the sha256 of the pdf file.  If omitted, we will
                compute it.  Possibly only used by testing code.
            slug: Filename slug for the pdf, or omit to take from the
                first input.  Possibly only used by testing code.
            force_render: Don't try to extract large bitmaps; always
                render the page.
            read_after: Automatically read the qr codes from the bundle after
                upload+splitting is finished.
            force: accept an upload that would otherwise be an error.
                Off by default.  Currently this allows duplicate bundles
                to be uploaded which would otherwise be an error.

        Returns:
            A dict of info about the new bundle, including the bundle_id
            (primary key), the bundle_name, a human-readable message
            of success, and then a human-readable list of warnings.

        Raises:
            ValidationError: _uploaded_pdf_file isn't a valid pdf or
                exceeds the page limit, or other error.
            PlomConflict: we already have a bundle which conflicts.
                ``force=True`` to accept it anyway.
        """
        warnings = []
        # TODO: the form used something else:
        # django.utils import timezone
        # timestamp = timezone.now()
        timestamp = datetime.timestamp(timezone.now())

        if not slug:
            filename_stem = Path(_uploaded_pdf_file.name).stem
            if filename_stem.startswith("_"):
                raise ValidationError(
                    "Bundle filenames cannot start with an underscore"
                    " - we reserve those for internal use."
                )
            slug = slugify(filename_stem)

        # Warning: Aidan saw errors if we open this more than once, during an API upload
        # here get the bytes from the file and never use `_upload_pdf_file` again.
        try:
            with _uploaded_pdf_file.open("rb") as fh:
                file_bytes = fh.read()
        except OSError as err:
            raise ValidationError(f"Unexpected error handling file: {err}") from err

        if len(file_bytes) > settings.MAX_BUNDLE_SIZE:
            raise ValidationError(
                f"Bundle file size {len(file_bytes)} exceeds"
                f" limit of {settings.MAX_BUNDLE_SIZE} bytes."
            )

        if not pdf_hash:
            pdf_hash = hashlib.sha256(file_bytes).hexdigest()

        try:
            with pymupdf.open(stream=file_bytes) as pdf_doc:
                if not pdf_doc.is_pdf:
                    raise ValidationError("File is not a valid PDF")
                # I'm not sure this check is any different but probably doesn't hurt
                if "PDF" not in pdf_doc.metadata["format"]:
                    raise ValidationError("File is not a valid PDF")

                if pdf_doc.is_repaired:
                    msg = "PyMuPDF had to repair this PDF: perhaps it is damaged in some way?"
                    # if not force:
                    #     raise ValidationError(msg)
                    warnings.append(msg)

                number_of_pages = pdf_doc.page_count
                if number_of_pages == 0:
                    raise ValidationError(
                        "File seems to contain no pages?  Perhaps it is not a valid PDF"
                    )
                if number_of_pages > settings.MAX_BUNDLE_PAGES:
                    raise ValidationError(
                        f"Uploaded pdf with {number_of_pages} pages"
                        f" exceeds {settings.MAX_BUNDLE_PAGES} page limit"
                    )
        # PyMuPDF docs says its exceptions will be caught by RuntimeError
        # (keep some other stuff just in case)
        except (RuntimeError, pymupdf.FileDataError, KeyError) as e:
            raise ValidationError(
                f"PyMuPDF library {pymupdf.__version__} could not open file,"
                f" perhaps not a PDF? {type(e).__name__}: {e} "
            ) from e
        except pymupdf.mupdf.FzErrorBase as e:
            # https://github.com/pymupdf/PyMuPDF/issues/3905
            # Drop this case once our minimum PyMuPDF >= 1.24.11
            raise ValidationError(
                f"Perhaps not a pdf file?  Unexpected error: {e}"
            ) from e

        # Warning: Issue #2888, and https://gitlab.com/plom/plom/-/merge_requests/2361
        # strange behaviour can result from relaxing this durable=True
        with transaction.atomic(durable=True):
            existing = StagingBundle.objects.filter(pdf_hash=pdf_hash)
            if existing:
                dupes = ", ".join(f'"{x.slug}"' for x in existing)
                N = len(existing)
                if N == 1:
                    msg = f"A bundle {dupes} has already been uploaded"
                else:
                    msg = f"{N} bundles {dupes} have already been uploaded"
                msg += f" with the same file hash {pdf_hash}"
                if not force:
                    raise PlomConflict(msg)
                warnings.append(msg)

            # if necessary, uniquify the slug with a random suffix
            # (we're inside a durable atomic: no race condition here)
            current_slugs = list(
                StagingBundle.objects.all().values_list("slug", flat=True)
            )
            if slug in current_slugs:
                _slug = slug
                slug = uniquify_str_against_list(_slug, current_slugs)
                warnings.append(
                    f'Using bundle name "{slug}" because "{_slug}" was not unique'
                )

            # create the bundle first, so it has a pk and
            # then give it the file and resave it.
            # TODO: not sure why this separation is important?  costs two DB ops...
            bundle_obj = StagingBundle.objects.create(
                slug=slug,
                user=user,
                timestamp=timestamp,
                pushed=False,
                force_page_render=force_render,
            )
            bundle_obj.pdf_file = File(BytesIO(file_bytes), name=f"{slug}.pdf")
            bundle_obj.pdf_hash = pdf_hash
            bundle_obj.number_of_pages = number_of_pages
            bundle_obj.save()
        cls.split_and_save_bundle_images(bundle_obj.pk, read_after=read_after)

        if len(pdf_hash) >= (12 + 12 + 3):
            brief_hash = pdf_hash[:12] + "..." + pdf_hash[-12:]
        else:
            brief_hash = pdf_hash
        msg = (
            f"Uploaded {slug} with {number_of_pages} pages "
            f"and hash {brief_hash}. "
            "Background processing started."
        )
        return {
            "bundle_id": bundle_obj.pk,
            "bundle_name": bundle_obj.slug,
            "msg": msg,
            "warnings": "; ".join(warnings),
        }

    @classmethod
    def upload_bundle_cmd(
        cls,
        pdf_file_path: str | pathlib.Path,
        username: str,
    ) -> dict[str, Any]:
        """Wrapper around upload_bundle for use by the commandline bundle upload command.

        Checks if the supplied username has permissions to access and upload scans.

        Args:
            pdf_file_path: the path to the pdf to be uploaded.
            username: the username string of who is uploading the file.

        Returns:
            A dict of info, as per :method:`upload_bundle`.

        Raises:
            ValueError: username invalid or not in scanner group.
            ValidationError: _uploaded_pdf_file isn't a valid pdf or
                exceeds the page limit, or other error.
            PlomConflict: duplicate upload.
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

        return cls.upload_bundle(pdf_file_object, user_obj)

    @staticmethod
    def split_and_save_bundle_images(
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
            x = PagesToImagesChore.objects.create(
                bundle=bundle_obj,
                status=HueyTaskTracker.STARTING,
            )
            tracker_pk = x.pk
        res = huey_parent_split_bundle_chore(
            bundle_pk,
            number_of_chunks,
            tracker_pk=tracker_pk,
            read_after=read_after,
            _debug_be_flaky=False,
        )
        # print(f"Just enqueued Huey parent_split_and_save task id={res.id}")
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

    @transaction.atomic
    def get_bundle_split_completions(self, bundle_pk: int) -> int:
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        return PagesToImagesChore.objects.get(bundle=bundle_obj).completed_pages

    def is_bundle_mid_splitting(self, bundle_pk: int) -> bool:
        """Check if the bundle with this id is currently in the midst of splitting its pages."""
        # TODO: use a prefetch to avoid two DB calls in this function
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        if bundle_obj.has_page_images:
            return False
        # If there are only Error/Complete chores then we are not splitting
        if PagesToImagesChore.objects.filter(
            bundle=bundle_obj,
            status__in=(
                HueyTaskTracker.TO_DO,
                HueyTaskTracker.STARTING,
                HueyTaskTracker.QUEUED,
                HueyTaskTracker.RUNNING,
            ),
        ).exists():
            return True
        return False

    def are_bundles_mid_splitting(self) -> dict[str, bool]:
        """Returns a dict of each staging bundle (slug) and whether it is still mid-split."""
        return {
            bundle_obj.slug: self.is_bundle_mid_splitting(bundle_obj.pk)
            for bundle_obj in StagingBundle.objects.all()
        }

    def remove_bundle_by_pk(self, bundle_pk: int) -> None:
        """Remove a bundle PDF from the filesystem + database.

        Note - as side-effect this removes the associated images
        from the filesystem and database.

        Args:
            bundle_pk: the primary key for a particular bundle.

        Exceptions:
            PlomBundleLockedException: bundle was splitting or reading QR
                codes, or "push-locked", or already pushed.
        """
        with transaction.atomic(durable=True):
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
            # start making a list of files to unlink - we do that after
            # all the DB ops are successful. Get the base image files
            files_to_unlink = [
                bimg.image_file.path
                for bimg in BaseImage.objects.filter(stagingimage__bundle=_bundle_obj)
            ]
            # and the thumbnails...
            # (note subtle difference in staging_image / stagingimage - sigh)
            files_to_unlink.extend(
                [
                    thb.image_file.path
                    for thb in StagingThumbnail.objects.filter(
                        staging_image__bundle=_bundle_obj
                    )
                ]
            )
            # and the bundle pdf
            files_to_unlink.append(_bundle_obj.pdf_file.path)
            # the base images in the bundle are not automatically
            # removed by deleting the bundle (fun with cascade deletes)
            # so we delete them here "by hand" - this has the side-effect
            # of deleting the staging_images they are attached to. the
            # thumbnails will then be automatically deleted by the deletion
            # of the staging_images.
            BaseImage.objects.filter(stagingimage__bundle=_bundle_obj).delete()
            # now safe to delete the bundle itself
            _bundle_obj.delete()

        # Now that all DB ops are done, the actual files are deleted OUTSIDE
        # of the durable atomic block. See the changes and discussions in
        # https://gitlab.com/plom/plom/-/merge_requests/3127
        for file_path in files_to_unlink:
            pathlib.Path(file_path).unlink()

    def remove_bundle_by_slug_cmd(self, bundle_slug: str) -> None:
        """Wrapper around remove_bundle_by_pk but takes bundle-slug instead."""
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_slug)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_slug}' does not exist!")
        self.remove_bundle_by_pk(bundle_obj.pk)

    @classmethod
    def get_original_image(cls, bundle_id: int, index: int) -> File:
        """Get the original, full-resolution image file from the database."""
        return cls.get_image(bundle_id, index).baseimage.image_file

    @staticmethod
    def check_for_duplicate_hash(pdf_hash: str) -> bool:
        """Check if a PDF has already been uploaded.

        Returns True if the hash already exists in the database.
        """
        return StagingBundle.objects.filter(pdf_hash=pdf_hash).exists()

    @staticmethod
    def get_bundle_name_from_hash(pdf_hash: str) -> str | None:
        """Get a bundle-name from a hash or return none."""
        try:
            return StagingBundle.objects.get(pdf_hash=pdf_hash).slug
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_bundle_from_pk(pk: int) -> StagingBundle:
        """Return a StagingBundle object from its pk."""
        return StagingBundle.objects.get(pk=pk)

    @staticmethod
    def get_image(bundle_id: int, index: int) -> StagingImage:
        """Get an image from the database from bundle-id, and index."""
        return StagingImage.objects.get(bundle__pk=bundle_id, bundle_order=index)

    @transaction.atomic
    def get_first_image(self, bundle_obj: StagingBundle) -> StagingImage:
        """Get the first image from the given bundle."""
        return StagingImage.objects.get(
            bundle=bundle_obj,
            bundle_order=1,
        )

    @transaction.atomic
    def get_thumbnail_image(self, bundle_pk: int, index: int) -> StagingImage:
        """Get a thumbnail image from the database.

        To uniquely identify an image, we need a bundle and a page index.
        """
        # try to do this in one query to reduce DB hits.
        img = StagingImage.objects.select_related("stagingthumbnail").get(
            bundle__pk=bundle_pk, bundle_order=index
        )
        return img.stagingthumbnail

    @transaction.atomic
    def get_n_images(self, bundle: StagingBundle) -> int:
        """Get the number of page images in a StagingBundle from the number of its StagingImages."""
        return bundle.stagingimage_set.count()

    @transaction.atomic
    def get_user_bundles(self, user: User) -> list[StagingBundle]:
        """Return all of the staging bundles that the given user uploaded."""
        return list(StagingBundle.objects.filter(user=user))

    @transaction.atomic
    def get_all_staging_bundles(self) -> list[StagingBundle]:
        """Return all of the staging bundles in reverse chronological order.

        Note - for each set we prefetch the associated user info and the
            info about the associated staging images.
        """
        return list(
            StagingBundle.objects.all().prefetch_related("user").order_by("-timestamp")
        )

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

    @staticmethod
    def parse_qr_code(list_qr_codes: list[dict[str, Any]]) -> dict[str, Any]:
        """Parse QR codes into list of dictionaries.

        Args:
            list_qr_codes: QR codes returned from QRextract() method as a dictionary

        Returns:
            groupings: (dict) Set of data from raw-qr-strings
            {
                'NE': {
                    'page_type': 'plom_qr',
                    'page_info': {
                        'paper_id': 1,
                        'page_num': 3,
                        'version_num': 1,
                        'public_code': '193849',
                    }
                    'quadrant': '1',
                    'tpv': '0000100301',
                    'x_coord': 2204,
                    'y_coord': 279.5
                },
                'SW': {
                    'page_type': 'plom_qr',
                    'page_info': {
                        'paper_id': 1,
                        'page_num': 3,
                        'version_num': 1,
                        'public_code': '193849',
                }
                    'quadrant': '3',
                    'tpv': '0000100301',
                    'x_coord': 234,
                    'y_coord': 2909.5
                },
                'SE': {
                    'page_type': 'plom_qr',
                    'page_info': {
                        'paper_id': 1,
                        'page_num': 3,
                        'version_num': 1,
                        'public_code': '193849',
                    }
                    'quadrant': '4',
                    'tpv': '0000100301',
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
            Similarly, if the page is a scrap-paper page, then returns
                    'SE': {
                    'page_type': 'plom_scrap',
                    'quadrant': '4',
                    'tpv': 'plomS',
                    'x_coord': 2203,
                    'y_coord': 2906.5
                }
            Similarly, if the page is a bundle-separator-paper page, then returns
                    'SE': {
                    'page_type': 'plom_bundle_separator',
                    'quadrant': '4',
                    'tpv': 'plomB',
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
                # note that from legacy-scan code the tpv_signature is the full raw "TTTTTPPPVVOCCCCCC" qr-string
                # while tpv refers to "TTTTTPPPVV"
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
                elif isValidBundleSeparatorPaperCode(raw_qr_string):
                    corner = parseExtraPageCode(raw_qr_string)
                    qr_code_dict.update(
                        {
                            "page_type": "plom_bundle_separator",
                            "quadrant": corner,
                            "tpv": "plomB",
                        }
                    )
                else:
                    # it is not a valid qr-code
                    qr_code_dict.update(
                        {
                            "page_type": "invalid_qr",
                            "quadrant": "0",
                        }
                    )
                groupings[quadrant] = qr_code_dict
        return groupings

    def read_qr_codes(self, bundle_pk: int) -> None:
        """Read QR codes of scanned pages in a bundle.

        Args:
            bundle_pk: primary key of bundle DB object
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        # check that the qr-codes have not been read already, or that a task has not been set

        # Currently, even a status Error chore would prevent it from being rerun
        if ManageParseQRChore.objects.filter(bundle=bundle_obj).exists():
            return

        with transaction.atomic(durable=True):
            x = ManageParseQRChore.objects.create(
                bundle=bundle_obj,
                status=HueyTaskTracker.STARTING,
            )
            tracker_pk = x.pk

        log.info("starting the read_qr_codes_chore...")
        res = huey_parent_read_qr_codes_chore(
            bundle_pk, tracker_pk=tracker_pk, _debug_be_flaky=False
        )
        # print(f"Just enqueued Huey parent_read_qr_codes task id={res.id}")
        HueyTaskTracker.transition_to_queued_or_running(tracker_pk, res.id)

    @staticmethod
    def map_bundle_page(
        bundle_id: int,
        page: int,
        *,
        user: User,
        papernum: int,
        question_indices: list[int],
    ) -> None:
        """Map one page of a staged bundle onto zero or more questions.

        After mapping, the page will have type EXTRA.

        Any page with one of the types UNKNOWN, ERROR, KNOWN, or DISCARD
        can be mapped. Only some pages of type EXTRA can be mapped:
        if the page already has mapping info, the request fails with
        PlomConflict.

        Args:
            bundle_id: unique integer identifier of bundle DB object.
            page: one-based index of the page in the bundle to be mapped.

        Keyword Args:
            user: who is doing this operation?
            papernum: the number of the target paper.
            question_indices: a variable-length list of which questions (by
                one-based question index) to attach the page to.
                It is an error if the list is empty.
                If the list is the singleton [MobilePage.DNM_qidx], the page
                gets attached to the DNM group for the given papernum.
                See comments in the code about this interpretation: other parts
                of the source tree do things differently!!

        Raises:
            ObjectDoesNotExist: no such BundleImage, e.g., invalid bundle id or page
            ValueError: other database things not found.
            PlomConflict: extra page already has data.
        """
        log.debug(
            f"Starting map_bundle_page with bundle_id={bundle_id}, page={page} "
            f"and target papernum={papernum}, question_indices={question_indices}."
        )

        if not question_indices:
            raise ValueError("You must supply a list of question indices")

        with transaction.atomic():
            page_img = StagingImage.objects.get(bundle__pk=bundle_id, bundle_order=page)

            # TODO: Check design assumptions here. We interpret [MobilePage.DNM_qidx]
            # as DNM. But the downstream bundle-pusher expects [] to indicate DNM.
            # Shout-out to check_question_list() found in plom/scan/question_list_utils.py,
            # where competing interpretations can be found.
            if question_indices == [MobilePage.DNM_qidx]:
                question_indices = []
            log.info(
                f"Mapping page with id {page_img.pk} and type {page_img.image_type} "
                f"to paper {papernum} with list {question_indices}."
            )
            if page_img.image_type != StagingImage.EXTRA:
                ScanCastService.extralise_image_from_bundle_id(user, bundle_id, page)
            ScanCastService.assign_extra_page_from_bundle_id_and_order(
                user,
                bundle_id,
                page,
                papernum,
                question_indices,
            )
            pi_updated = StagingImage.objects.get(
                bundle__pk=bundle_id, bundle_order=page
            )
            log.debug(
                f"After update, id is {pi_updated.pk} and type is {pi_updated.image_type}."
            )

            # TODO: Issue #3770.
            # bundle_obj = (
            #     StagingBundle.objects.filter(pk=bundle_pk).select_for_update().get()
            # )
            # finally - mark the bundle as having had its qr-codes read.
            # bundle_obj.has_qr_codes = True
            # bundle_obj.save()

    @classmethod
    def discard_staging_bundle_page(
        cls, bundle_id: int, page: int, *, user: User
    ) -> None:
        """Discard one page of a staged bundle.

        Any page with one of the types UNKNOWN, ERROR, KNOWN, or DISCARD
        can be discarded.  This is a frontend to some lower-level routines:
        at a lower-level it is an error to re-discard an already discarded
        page so this routine checks and does a no-op if the page is already
        discarded.

        Args:
            bundle_id: unique integer identifier of bundle DB object.
            page: one-based index of the page in the bundle to be discarded.

        Keyword Args:
            user: who is doing this operation?

        Raises:
            ObjectDoesNotExist: no such BundleImage, e.g., invalid bundle id or page
            PermissionDenied: not in the scanner group.
            ValueError: May be raised by supporting methods from class ScanCastService.
        """
        log.debug(f"Starting discard of bundle_id={bundle_id}, page={page}")

        with transaction.atomic():
            page_img = StagingImage.objects.get(bundle__pk=bundle_id, bundle_order=page)

            log.info(f"Trying to mark page with id {page_img.pk} for DISCARD.")
            if page_img.image_type != StagingImage.DISCARD:
                ScanCastService.discard_image_type_from_bundle_id_and_order(
                    user, bundle_id, page
                )
            pi_updated = StagingImage.objects.get(
                bundle__pk=bundle_id, bundle_order=page
            )
            log.debug(
                f"After update, id is {pi_updated.pk} and type is {pi_updated.image_type}."
            )

    @transaction.atomic
    def get_bundle_qr_completions(self, bundle_pk: int) -> int:
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        return ManageParseQRChore.objects.get(bundle=bundle_obj).completed_pages

    def is_bundle_mid_qr_read(self, bundle_pk: int) -> bool:
        """Check if the bundle with this id is currently in the midst of reading QR codes."""
        # TODO: use a prefetch to avoid two DB calls in this function
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        if bundle_obj.has_qr_codes:
            return False

        # If there are only Error/Complete chores then we are not reading
        if ManageParseQRChore.objects.filter(
            bundle=bundle_obj,
            status__in=(
                HueyTaskTracker.TO_DO,
                HueyTaskTracker.STARTING,
                HueyTaskTracker.QUEUED,
                HueyTaskTracker.RUNNING,
            ),
        ).exists():
            return True
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
    def get_n_unread_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.UNREAD).count()

    @transaction.atomic
    def get_n_unknown_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.UNKNOWN).count()

    @transaction.atomic
    def get_n_extra_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.EXTRA).count()

    @transaction.atomic
    def get_n_extra_images_with_data(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(
            image_type=StagingImage.EXTRA,
            paper_number__isnull=False,
            question_idx_list__isnull=False,
        ).count()

    @classmethod
    def do_all_extra_images_in_bundle_have_data(cls, bundle: StagingBundle) -> bool:
        """Check whether all extra pages in a bundle have paper-numbers and questions."""
        extras = bundle.stagingimage_set.filter(image_type=StagingImage.EXTRA)
        return cls.do_all_these_extra_images_have_data(extras)

    @staticmethod
    def do_all_these_extra_images_have_data(extras: QuerySet[StagingImage]) -> bool:
        """Check whether a given collection of extra pages have paper-numbers and questions."""
        extras_with_complete_data = extras.filter(
            paper_number__isnull=False, question_idx_list__isnull=False
        )
        return not extras.difference(extras_with_complete_data).exists()

    @transaction.atomic
    def get_n_error_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.ERROR).count()

    @transaction.atomic
    def get_n_discard_images(self, bundle: StagingBundle) -> int:
        return bundle.stagingimage_set.filter(image_type=StagingImage.DISCARD).count()

    @transaction.atomic
    def staging_bundle_status(
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
                count = PagesToImagesChore.objects.get(bundle=bundle).completed_pages
                total_pages = f"in progress: {count} of {bundle.number_of_pages}"
            else:
                total_pages = images.count()

            bundle_qr_read = bundle.has_qr_codes
            if self.is_bundle_mid_qr_read(bundle.pk):
                count = ManageParseQRChore.objects.get(bundle=bundle).completed_pages
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

    @classmethod
    def is_bundle_perfect(cls, bundle_pk: int) -> bool:
        """Checks if the bundle (given by its pk) is perfect.

        A bundle is perfect when
          * no unread pages, no error-pages, no unknown-pages, and
          * all extra pages have data.
        this, in turn, means that all pages present in bundle are
          * known or discard, or
          * are extra-pages with data
        """
        bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
        return cls._is_bundle_obj_perfect(bundle_obj)

    @staticmethod
    @transaction.atomic
    def _is_bundle_obj_perfect(bundle_obj: StagingBundle) -> bool:
        """Checks if the bundle object is perfect."""
        # check for unread, unknown, error pages
        if bundle_obj.stagingimage_set.filter(
            image_type__in=[
                StagingImage.UNKNOWN,
                StagingImage.UNREAD,
                StagingImage.ERROR,
            ]
        ).exists():
            return False
        # check for extra pages not assigned to paper numbers
        epages = bundle_obj.stagingimage_set.filter(image_type=StagingImage.EXTRA)
        if epages.filter(paper_number__isnull=True).exists():
            return False
        return True

    @classmethod
    def are_bundles_perfect(cls) -> dict[str, bool]:
        """Returns a dict of each staging bundle (slug) and whether it is perfect."""
        return {
            bundle_obj.slug: cls._is_bundle_obj_perfect(bundle_obj)
            for bundle_obj in StagingBundle.objects.all().prefetch_related(
                "stagingimage_set"
            )
        }

    @staticmethod
    def are_bundles_pushed() -> dict[str, bool]:
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

    @classmethod
    def push_bundle_to_server(cls, bundle_obj_pk: int, user_obj: User) -> None:
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
            ValueError: When the bundle is not perfect (eg still has errors or unknowns),
            PlomPushCollisionException: When images in the bundle collide with existing pushed images
            PlomBundleLockedException: When any bundle is push-locked, or the current one is locked/push-locked.
            ObjectDoesNotExist: no such bundle.
            RuntimeError: When something very strange happens!!
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
            if not cls._is_bundle_obj_perfect(bundle_obj):
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
                ImageBundleService.push_valid_bundle(bundle_obj, user_obj)
                # now update the bundle and its images to say "pushed"
                bundle_obj.stagingimage_set.update(pushed=True)
                bundle_obj.pushed = True
                bundle_obj.save()
        except PlomPushCollisionException as err:
            raise_this_after = err
        except RuntimeError as err:
            # This should only be for **very bad** (unexpected) errors
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

    @staticmethod
    @transaction.atomic
    def get_bundle_pages_info_list(bundle_obj: StagingBundle) -> list[dict[str, Any]]:
        """List of info about the pages in a bundle in bundle order.

        Args:
            bundle_obj: reference to a bundle.

        Returns:
            list: the pages within the given bundle ordered by their
            bundle-order.  Each item in the list is a dict with keys
            ``status`` (the image type), ``order``, ``rotation``,
            ``page_label``, ``n_qr_read``, ``zfill_order``, and ``info``.
            The latter value is itself a dict containing different
            items depending on the image-type.  For error-pages and
            discard-pages, it contains the ``reason`` while for
            known-pages it contains ``paper_number``, ``page_number``
            and ``version``.  Finally for extra-pages, it contains
            ``paper_number``, and ``question_idx_list``.
            ``page_label`` is a short label appropriate for displaying
            on a page icon, or as a tooltip.
            ``zfill_order`` is just order with zero-padding based on
            the number of digits needed for size of this bundle.
            ``n_qr_read`` is the number of QR codes read, and appears
            to be unused by anyone as of 2025-Oct.
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
                "order": f"{img.bundle_order}",
                "zfill_order": f"{img.bundle_order}".zfill(n_digits),
                "rotation": img.rotation,
                "n_qr_read": len(img.parsed_qr),
                "page_label": "",  # filled-in below
            }

        for img in bundle_obj.stagingimage_set.filter(image_type=StagingImage.ERROR):
            pages[img.bundle_order]["info"] = {"reason": img.error_reason}

        for img in bundle_obj.stagingimage_set.filter(image_type=StagingImage.DISCARD):
            pages[img.bundle_order]["info"] = {"reason": img.discard_reason}

        for img in bundle_obj.stagingimage_set.filter(image_type=StagingImage.KNOWN):
            pages[img.bundle_order]["info"] = {
                "paper_number": img.paper_number,
                "page_number": img.page_number,
                "version": img.version,
            }
        for img in bundle_obj.stagingimage_set.filter(image_type=StagingImage.EXTRA):
            pages[img.bundle_order]["info"] = {
                "paper_number": img.paper_number,
                "question_idx_list": img.question_idx_list,
            }

        # now build an ordered list by running the keys (which are bundle-order) of the pages-dict in order.
        r = [pages[ord] for ord in sorted(pages.keys())]

        # generate the page labels
        for pg in r:
            status = pg["status"]
            info = pg["info"]
            if status == "known":
                label = f"paper-{info['paper_number']}.{info['page_number']}"
            elif status == "unknown":
                label = "Unknown page"
            elif status == "extra":
                label = "Extra page"
                if pg["info"]["paper_number"]:
                    label += f" {info['paper_number']}."
                    qidx_list = info["question_idx_list"]
                    if not qidx_list:
                        # TODO: seems to use [] rather than the MobilePage.DNM_qidx
                        # not quite sure why but seems like something that might
                        # bite us later
                        label += "DNM"
                    elif len(qidx_list) == 1:
                        label += f"qidx{qidx_list[0]}"
                    else:
                        label += "qidx[" + ",".join(str(x) for x in qidx_list) + "]"
                else:
                    label += " - " + _("no data")
            elif status == "error":
                label = f"error: {info['reason']}"
            elif status == "unread":
                label = "qr-unread"
            elif status == "discard":
                label = f"discard: {info['reason']}"
            else:
                raise RuntimeError(f"Programming error: unexpected case pg={pg}")
                # label = "unexpected error"
            pg["page_label"] = label

        return r

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
        for known in StagingImage.objects.filter(
            bundle=bundle_obj, image_type=StagingImage.KNOWN
        ).order_by("paper_number", "page_number"):
            papers.setdefault(known.paper_number, []).append(
                {
                    "type": "known",
                    "page": known.page_number,
                    "order": known.bundle_order,
                }
            )
        # Now loop over the extra pages
        for extra in StagingImage.objects.filter(
            bundle=bundle_obj, image_type=StagingImage.EXTRA
        ).order_by("paper_number", "question_idx_list"):
            # we can skip those without data
            if extra.paper_number:
                papers.setdefault(extra.paper_number, []).append(
                    {
                        "type": "extra",
                        "question_idx_list": extra.question_idx_list,
                        "order": extra.bundle_order,
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
                    "paper_number": img.paper_number,
                    "question_idx_list": img.question_idx_list,
                },
                "order": f"{img.bundle_order}",
                "zfill_order": f"{img.bundle_order}".zfill(n_digits),
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
            "order": f"{img.bundle_order}",
            "zfill_order": f"{img.bundle_order}".zfill(n_digits),
            "rotation": img.rotation,
            "qr_codes": img.parsed_qr,
            "history": img.history,
        }
        if img.image_type == StagingImage.ERROR:
            info = {"reason": img.error_reason}
        elif img.image_type == StagingImage.DISCARD:
            info = {"reason": img.discard_reason}
        elif img.image_type == StagingImage.KNOWN:
            info = {
                "paper_number": img.paper_number,
                "page_number": img.page_number,
                "version": img.version,
            }
        elif img.image_type == StagingImage.EXTRA:
            _render = SpecificationService.render_html_flat_question_label_list
            info = {
                "paper_number": img.paper_number,
                "question_idx_list": img.question_idx_list,
                "question_list_html": _render(img.question_idx_list),
            }
        else:
            info = {}

        current_page.update({"info": info})
        return current_page

    @staticmethod
    def get_bundle_paper_numbers(bundle_obj: StagingBundle) -> list[int]:
        """Return a sorted list of paper-numbers in the given bundle as determined by known and extra pages."""
        paper_list = []

        for img in StagingImage.objects.filter(
            bundle=bundle_obj, image_type=StagingImage.KNOWN
        ):
            paper_list.append(img.paper_number)

        for img in StagingImage.objects.filter(
            bundle=bundle_obj, image_type=StagingImage.EXTRA
        ):
            if img.paper_number:
                paper_list.append(img.paper_number)

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
        ):
            papers_pages.setdefault(img.paper_number, [])
            papers_pages[img.paper_number].append(img.page_number)

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
        ):
            papers_pages.setdefault(img.paper_number, 0)
            papers_pages[img.paper_number] += 1

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
                    "order": f"{img.bundle_order}",
                    "zfill_order": f"{img.bundle_order}".zfill(n_digits),
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
        """Get information about the discard pages within the given staged bundle."""
        # compute number of digits in longest page number to pad the page numbering
        n_digits = len(str(bundle_obj.number_of_pages))
        pages = []
        for img in (
            bundle_obj.stagingimage_set.filter(image_type=StagingImage.DISCARD)
            .all()
            .order_by("bundle_order")
        ):
            pages.append(
                {
                    "status": img.image_type,
                    "order": f"{img.bundle_order}",
                    "zfill_order": f"{img.bundle_order}".zfill(n_digits),
                    "rotation": img.rotation,
                    "reason": img.discard_reason,
                }
            )
        return pages

    @transaction.atomic
    def get_bundle_discard_pages_info_cmd(
        self, bundle_name: str
    ) -> list[dict[str, Any]]:
        """Wrapper around get_bundle_discard_pages_info function."""
        try:
            bundle_obj = StagingBundle.objects.get(slug=bundle_name)
        except ObjectDoesNotExist:
            raise ValueError(f"Bundle '{bundle_name}' does not exist!")
        return self.get_bundle_discard_pages_info(bundle_obj)

    def get_bundle_colliding_images(self, bundle_obj: StagingBundle) -> list[int]:
        """Return a list of orders ("pages") in this bundle that collide with pushed images."""
        # shortcut - assume a pushed bundle has no collisions
        if bundle_obj.pushed:
            return []

        staging_images = StagingImage.objects.filter(bundle=bundle_obj)
        colliding_staging_images = ImageBundleService._find_external_collisions(
            staging_images
        )

        colliding_orders = list(
            colliding_staging_images.values_list("bundle_order", flat=True)
        )
        return sorted(colliding_orders)


# ----------------------------------------
# factor out the huey tasks.
# ----------------------------------------


# The decorated function returns a ``huey.api.Result``
@db_task(queue="parentchores", context=True)
def huey_parent_split_bundle_chore(
    bundle_pk: int,
    number_of_chunks: int,
    *,
    tracker_pk: int,
    read_after: bool = False,
    _debug_be_flaky: bool = False,
    task: huey.api.Task | None = None,
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
        task: includes our ID in the Huey process queue.  This kwarg is
            passed by `context=True` in decorator: callers should not
            pass this in!

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".

    Raises:
        ValueError: various error situations about the input.
        RuntimeError: child chore failed.
        AssertionError: unexpected situations, such as zero-length bundle.
    """
    assert task is not None

    start_time = time.time()
    bundle_obj = StagingBundle.objects.get(pk=bundle_pk)
    bundle_length = bundle_obj.number_of_pages
    assert bundle_length is not None, "Should know bundle length before processing"
    assert bundle_length > 0, "Bundle length should be non-zero"

    HueyTaskTracker.transition_to_running(tracker_pk, task.id)

    # cut the list of all indices into chunks
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
                _debug_be_flaky=_debug_be_flaky,
            )
            for ord_chnk in order_chunks
        ]

        # results = [X.get(blocking=True) for X in task_list]
        n_tasks = len(task_list)
        while True:
            # list items are None (if not completed) or list [dict of page info]
            try:
                result_chunks = [X.get() for X in task_list]
            except huey.exceptions.TaskException as e:
                print(f"Parent: child image split chore failed with {e}")
                log.error("Parent: child image split chore failed with %s", str(e))
                # make an attempt to stop any remaining unqueued child tasks.
                # note those already started probably will not stop.
                for chore in task_list:
                    log.info("Parent: trying to revoke child chore %s", chore)
                    chore.revoke()
                raise RuntimeError(f"child task failed image split: {e}") from e

            # remove all the nones to get list of completed tasks
            not_none_result_chunks = [
                chunk for chunk in result_chunks if chunk is not None
            ]
            completed_tasks = len(not_none_result_chunks)
            # flatten that list of lists to get a list of rendered pages
            results = [X for chunk in not_none_result_chunks for X in chunk]
            rendered_page_count = len(results)

            with transaction.atomic():
                _task = PagesToImagesChore.objects.select_for_update().get(
                    bundle=bundle_obj
                )
                _task.completed_pages = rendered_page_count
                _task.save()

            if completed_tasks == n_tasks:
                break
            else:
                time.sleep(1)

        with transaction.atomic():
            for X in results:
                with open(X["file_path"], "rb") as fh:
                    bimg = BaseImage.objects.create(
                        image_file=File(fh, name=X["file_name"]),
                        image_hash=X["image_hash"],
                    )
                    img = StagingImage.objects.create(
                        bundle=bundle_obj,
                        bundle_order=X["order"],
                        image_type=StagingImage.UNREAD,
                        baseimage=bimg,
                        history=f"Created in bundle {bundle_obj.id} order {X['order']}",
                    )
                with open(X["thumb_path"], "rb") as fh:
                    StagingThumbnail.objects.create(
                        staging_image=img, image_file=File(fh, X["thumb_name"])
                    )

            # get a new reference for updating the bundle itself
            _write_bundle = StagingBundle.objects.select_for_update().get(pk=bundle_pk)
            _write_bundle.has_page_images = True
            _write_bundle.time_to_make_page_images = time.time() - start_time
            _write_bundle.save()

    HueyTaskTracker.transition_to_complete(tracker_pk)
    # if requested automatically queue qr-code reading
    if read_after:
        ScanService().read_qr_codes(bundle_pk)
    return True


# The decorated function returns a ``huey.api.Result``
@db_task(queue="parentchores", context=True)
def huey_parent_read_qr_codes_chore(
    bundle_pk: int,
    *,
    tracker_pk: int,
    _debug_be_flaky: bool = False,
    task: huey.api.Task | None = None,
) -> bool:
    """Read the QR codes of a bunch of pages.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        bundle_pk: StagingBundle object primary key

    Keyword Args:
        tracker_pk: a key into the database for anyone interested in
            our progress.
        task: includes our ID in the Huey process queue.  This kwarg is
            passed by `context=True` in decorator: callers should not
            pass this in!

    Returns:
        True, no meaning, just as per the Huey docs: "if you need to
        block or detect whether a task has finished".
    """
    assert task is not None

    start_time = time.time()

    HueyTaskTracker.transition_to_running(tracker_pk, task.id)

    bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

    task_list = [
        huey_child_parse_qr_code(page.pk, _debug_be_flaky=_debug_be_flaky)
        for page in bundle_obj.stagingimage_set.all()
    ]

    # results = [X.get(blocking=True) for X in task_list]

    n_tasks = len(task_list)
    while True:
        try:
            results = [X.get() for X in task_list]
        except huey.exceptions.TaskException as e:
            print(f"Parent: child QR read chore failed with {e}")
            log.error("Parent: child QR read chore failed with %s", str(e))
            # TODO: what about the child tasks still running?
            raise RuntimeError(f"child task failed QR read: {e}") from e

        count = sum(1 for X in results if X is not None)

        with transaction.atomic():
            _task = ManageParseQRChore.objects.select_for_update().get(
                bundle=bundle_obj
            )
            _task.completed_pages = count
            _task.save()

        if count == n_tasks:
            break
        else:
            time.sleep(1)

    with transaction.atomic():
        for X in results:
            # TODO - check for error status here.
            img = StagingImage.objects.select_for_update().get(pk=X["image_pk"])
            img.parsed_qr = X["parsed_qr"]
            img.rotation = X["rotation"]
            img.history += f"; {len(X['parsed_qr'])} QR codes read, rotation set to {X['rotation']}"
            img.save()
            # the thumbnail may need rotation.
            if img.rotation:
                update_thumbnail_after_rotation(img, img.rotation)

        # get a new reference for updating the bundle itself
        _write_bundle = StagingBundle.objects.select_for_update().get(pk=bundle_pk)
        _write_bundle.has_qr_codes = True
        _write_bundle.time_to_read_qr = time.time() - start_time
        _write_bundle.save()

    bundle_obj.refresh_from_db()
    # this could unexpected raise ValueError errors which would be caught
    # by the general catch-all handler
    QRService.classify_staging_images_based_on_QR_codes(bundle_obj)

    HueyTaskTracker.transition_to_complete(tracker_pk)
    return True


# The decorated function returns a ``huey.api.Result``
@db_task(queue="chores", context=True)
def huey_child_get_page_images(
    bundle_pk: int,
    order_list: list[int],
    basedir: pathlib.Path,
    *,
    _debug_be_flaky: bool = False,
    task: huey.api.Task | None = None,
) -> list[dict[str, Any]]:
    """Render page images and save to disk in the background.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        bundle_pk: bundle DB object's primary key
        order_list: a list of bundle orders of pages to extract - 1-indexed
        basedir (pathlib.Path): were to put the image
        _debug_be_flaky: for debugging, all take a while and some
            percentage will fail.
        task: includes our ID in the Huey process queue.  This is added
            by the `context=True` in decorator: callers in our code should
            not pass this in!

    Returns:
        Information about the page image, including its file name,
        thumbnail, hash etc.
    """
    import pymupdf
    from plom.scan import rotate
    from PIL import Image

    assert task is not None
    log.debug("Huey debug, we are task %s with id %s", task, task.id)
    # HueyTaskTracker.transition_to_running(tracker_pk, task.id)

    bundle_obj = StagingBundle.objects.get(pk=bundle_pk)

    rendered_page_info = []

    with pymupdf.open(bundle_obj.pdf_file.path) as pdf_doc:
        for order in order_list:
            if _debug_be_flaky:
                print(f"Huey debug, random sleep in task {task.id}")
                log.debug("Huey debug, random sleep in task %d", task.id)
                time.sleep(random.random() * 4)
                if random.random() < 0.04:
                    raise RuntimeError("Flaky simulated image split failure")
            basename = f"page_{bundle_obj.pk:03}_{order:05}"
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
                # log.info(f"{basename}: PyMuPDF render. No extract b/c: " + "; ".join(msgs))
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
@db_task(queue="chores", context=True)
def huey_child_parse_qr_code(
    image_pk: int,
    *,
    _debug_be_flaky: bool = False,
    task: huey.api.Task | None = None,
) -> dict[str, Any]:
    """Huey task to parse QR codes, check QR errors, and save to database in the background.

    It is important to understand that running this function starts an
    async task in queue that will run sometime in the future.

    Args:
        image_pk: primary key of the image

    Keyword Args:
        _debug_be_flaky: for debugging, all take a while and some
            percentage will fail.
        task: includes our ID in the Huey process queue.  This is added
            by the `context=True` in decorator: callers in our code should
            not pass this in!

    Returns:
        Information about the QR codes.
    """
    assert task is not None
    log.debug("Huey debug, we are task %s with id %s", task, task.id)

    staging_img = StagingImage.objects.get(pk=image_pk)
    # TODO: Issue #3888 this `.path` assumes storage is local and will fail
    # with a NotImplementedError when FileField uses remote storage.
    # TODO: refactor the rotation stuff to work with FieldFile:
    # image_fieldfile = staging_img.baseimage.image_file
    image_path = staging_img.baseimage.image_file.path

    code_dict = QRextract(image_path)

    page_data = ScanService.parse_qr_code([code_dict])

    if _debug_be_flaky:
        print(f"Huey debug, random sleep in task {task.id}")
        log.debug("Huey debug, random sleep in task %d", task.id)
        time.sleep(random.random() * 4)
        if random.random() < 0.04:
            raise RuntimeError("Flaky simulated QR read failure")

    rotation = PageImageProcessor.get_rotation_angle_or_None_from_QRs(page_data)

    # Andrew wanted to leave the possibility of re-introducing hard
    # rotations in the future, such as `plom.scan.rotate_bitmap`.

    # Re-read QR codes if the page image needs to be rotated
    if rotation and rotation != 0:
        code_dict = QRextract(image_path, rotation=rotation)
        page_data = ScanService.parse_qr_code([code_dict])
        # qr_error_checker.check_qr_codes(page_data, image_path, bundle)

    # Return the parsed QR codes for parent process to store in db
    return {
        "image_pk": image_pk,
        "parsed_qr": page_data,
        "rotation": rotation,
    }

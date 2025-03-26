# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

import hashlib
from io import BytesIO
import pathlib
from typing import Any


import pymupdf

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User

from plom_server.Base.models import BaseImage
from plom_server.Papers.models import (
    Bundle,
    Image,
    FixedPage,
    DiscardPage,
    IDPage,
    DNMPage,
)
from plom_server.Papers.services import SpecificationService
from plom_server.Preparation.services import SourceService
from ..services import ManageDiscardService, ManageScanService

# Info about the system bundle of substitute pages to use when a paper
# is missing pages (needed b/c all images must belong to bundles)
system_substitute_images_bundle_name = "__system_substitute_pages_bundle__"
system_substitute_images_bundle_hash = "bundle_for_substitute_pages"
font_size_for_forgiven_blurb = 36
page_not_submitted_text = "Page Not Submitted"


def create_system_bundle_of_substitute_pages() -> bool:
    """Create the system substitute pages and bundle database object.

    Returns:
        True if the substitutions bundle and its constutuent images were
        created.  False if they already existed (it is safe to call it
        repeatedly.

    The call is "atomic": either both the bundle AND its constituent images
    are created or neither occurs.

    Warning: this can be rather slow for large number of pages / versions.
    """
    with transaction.atomic():
        try:
            bundle_obj = Bundle.objects.create(
                name=system_substitute_images_bundle_name,
                pdf_hash=system_substitute_images_bundle_hash,
                _is_system=True,
            )
        except IntegrityError:
            # it already exists; we must have already made it
            return False

        # We are making a new one, so make images within the same atomic block
        assert bundle_obj.image_set.count() == 0
        _create_all_substitute_pages(bundle_obj)
        # if we're *not* making a bundle (b/c it already exists) then no
        # action is required; let the transaction expire.
    return True


def _create_substitute_page_images_for_forgiveness_bundle() -> list[dict[str, Any]]:
    """Create all the substitute page pixmaps for missing pages.

    Returns:
        List of dicts with keys ``page``, ``version``, ``name`` (a
        suggested image file), ``bytes`` (the bytes of the image,
        probably as PNG data).
    """
    version_list = SpecificationService.get_list_of_versions()
    page_list = SpecificationService.get_list_of_pages()  # 1-indexed
    image_list = []
    for v in version_list:
        doc = pymupdf.Document(stream=SourceService.get_source_as_bytes(v))
        for pg in page_list:
            the_page = doc[pg - 1]  # 0-indexed
            the_rect = the_page.rect
            pns_length = pymupdf.get_text_length(
                page_not_submitted_text, fontsize=font_size_for_forgiven_blurb
            )
            text_start = (
                (the_rect.width - pns_length) // 2,
                the_rect.height // 10 + font_size_for_forgiven_blurb,
            )
            text_box = pymupdf.Rect(
                text_start[0] - 8,
                text_start[1] - font_size_for_forgiven_blurb,
                text_start[0] + 8 + pns_length,
                text_start[1] + font_size_for_forgiven_blurb * 0.3,
            )
            the_page.draw_rect(
                text_box,
                width=0.5,
                color=(1, 1, 1),
                fill=(1, 1, 1),
                radius=0.02,
                fill_opacity=0.75,
            )
            the_page.insert_text(
                text_start,
                page_not_submitted_text,
                fontsize=font_size_for_forgiven_blurb,
                color=(1, 0, 0),
            )
            text_start = (
                (the_rect.width - pns_length) // 2,
                9 * the_rect.height // 10 + font_size_for_forgiven_blurb,
            )
            text_box = pymupdf.Rect(
                text_start[0] - 8,
                text_start[1] - font_size_for_forgiven_blurb,
                text_start[0] + 8 + pns_length,
                text_start[1] + font_size_for_forgiven_blurb * 0.3,
            )
            the_page.draw_rect(
                text_box,
                width=0.5,
                color=(1, 1, 1),
                fill=(1, 1, 1),
                radius=0.02,
                fill_opacity=0.75,
            )
            the_page.insert_text(
                text_start,
                page_not_submitted_text,
                fontsize=font_size_for_forgiven_blurb,
                color=(1, 0, 0),
            )
            text_blob = f"Substitute Page {pg}"
            text_blob_length = pymupdf.get_text_length(
                text_blob, fontsize=font_size_for_forgiven_blurb
            )
            text_start = (
                (the_rect.width - text_blob_length) // 2,
                the_rect.height // 2,
            )
            text_box = pymupdf.Rect(
                text_start[0] - 8,
                text_start[1] - font_size_for_forgiven_blurb,
                text_start[0] + 8 + text_blob_length,
                text_start[1] + font_size_for_forgiven_blurb * 0.3,
            )
            the_page.draw_rect(
                text_box,
                width=0.5,
                color=(1, 1, 1),
                fill=(1, 1, 1),
                radius=0.02,
                fill_opacity=0.75,
            )
            the_page.insert_text(
                text_start,
                text_blob,
                fontsize=font_size_for_forgiven_blurb,
                color=(1, 0, 0),
            )
            image_name = f"__forgive_v{v}_p{pg}.png"
            image_bytes = the_page.get_pixmap(dpi=200, annots=True).tobytes(
                output="png"
            )
            image_list.append(
                {
                    "version": v,
                    "page_number": pg,
                    "name": image_name,
                    "bytes": image_bytes,
                }
            )
    return image_list


def _create_all_substitute_pages(sys_sub_bundle_obj: Bundle) -> None:
    """Create the substitute page images and populate the given bundle with them.

    The system substitute image bundle is populated with a substitute image for
    each page/version of the assessment. If the assessment has n_pages pages,
    then the substitute image for page p of version v is created at
    bundle-order v*n_pages + p.
    """
    n_pages = SpecificationService.get_n_pages()
    image_list = _create_substitute_page_images_for_forgiveness_bundle()
    for n, img_dat in enumerate(image_list):
        bundle_order = img_dat["version"] * n_pages + img_dat["page_number"]
        image_name = img_dat["name"]
        image_bytes = img_dat["bytes"]
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        image_file = File(BytesIO(image_bytes), name=image_name)
        bimg = BaseImage.objects.create(image_file=image_file, image_hash=image_hash)
        Image.objects.create(
            bundle=sys_sub_bundle_obj,
            bundle_order=bundle_order,
            original_name=image_name,
            baseimage=bimg,
            parsed_qr={},
            rotation=0,
        )


def get_substitute_image(page_number: int, version: int) -> Image:
    """Return the substitute Image-object for the given page/version.

    Raises:
        ObjectDoesNotExist: Specifically ``Bundle.DoesNotExist`` if the
            the substitution bundle has not been built yet.
        ObjectDoesNotExist: probably Image.DoesNotExist if the pgae number
            or version are out of range, TODO: but this is not tested.
    """
    bundle_obj = Bundle.objects.get(name=system_substitute_images_bundle_name)
    # bundle_order = version*number of pages + page_number
    n_pages = SpecificationService.get_n_pages()  # 1-indexed
    bundle_order = n_pages * version + page_number
    return Image.objects.select_related("baseimage").get(
        bundle=bundle_obj, bundle_order=bundle_order
    )


def get_substitute_image_from_pk(image_pk: int) -> Image:
    """Return the Image object with the given pk."""
    return Image.objects.select_related("baseimage").get(pk=image_pk)


def erase_all_substitute_images_and_their_bundle() -> None:
    """Delete all the images from the system substitute image bundle."""
    # note that the parent caller (set papers printed) is a durable
    # transaction, so this does not have to be.
    with transaction.atomic(durable=True):
        try:
            sys_sub_bundle_obj = Bundle.objects.get(
                name=system_substitute_images_bundle_name
            )
        except Bundle.DoesNotExist:
            # nothing needs done if no bundle
            return
        # get the image files to unlink - do that after the
        # db objects are successfully deleted
        base_images_to_delete = BaseImage.objects.filter(
            image__bundle=sys_sub_bundle_obj
        )
        files_to_unlink = [bimg.image_file.path for bimg in base_images_to_delete]
        # carefully delete the Image objects before we delete the base-image objects
        # (they are protected).
        sys_sub_bundle_obj.image_set.all().delete()
        sys_sub_bundle_obj.delete()
        base_images_to_delete.delete()

    # Now that all DB ops are done, the actual files are deleted OUTSIDE
    # of the durable atomic block. See the changes and discussions in
    # https://gitlab.com/plom/plom/-/merge_requests/3127
    for file_path in files_to_unlink:
        pathlib.Path(file_path).unlink()


def forgive_missing_fixed_page(
    user_obj: User, paper_number: int, page_number: int
) -> None:
    """Replace the given fixed page with a substitute page image.

    Args:
        user_obj: the user-object who is doing the forgiving.
        paper_number: the paper
        page_number: the page from the paper that is missing.

    Raises:
        ValueError: If the fixed-page of the given paper/page does not exist.
        ValueError: If the paper/page does exist (has actually been scanned)
            but the corresponding fixed-page object has an image.
    """
    try:
        fixedpage_obj = FixedPage.objects.get(
            paper__paper_number=paper_number, page_number=page_number
        )
    except FixedPage.DoesNotExist as e:
        raise ValueError(
            f"Cannot find FixedPage of paper {paper_number} page {page_number}: {e}"
        ) from e
    if fixedpage_obj.image:
        raise ValueError(
            f"Paper {paper_number} page {page_number} already has an image"
            " - there is nothing to forgive!"
        )
    image_obj = get_substitute_image(page_number, fixedpage_obj.version)
    # create a discard page, move it into place via assign_discard_page_to_fixed_page
    discardpage_obj = DiscardPage.objects.create(
        image=image_obj,
        discard_reason=(
            "System-created page to substitute for"
            f" paper {paper_number} page {page_number}"
        ),
    )
    ManageDiscardService().assign_discard_page_to_fixed_page(
        user_obj, discardpage_obj.pk, paper_number, page_number
    )


def forgive_missing_fixed_page_cmd(
    username: str, paper_number: int, page_number: int
) -> None:
    """Simple wrapper around forgive_missing_fixed_page.

    Raises:
        ValueError: when the given username does not exist or has wrong
            permissions.
    """
    try:
        user_obj = User.objects.get(username__iexact=username, groups__name="manager")
    except ObjectDoesNotExist as e:
        raise ValueError(
            f"User '{username}' does not exist or has wrong permissions."
        ) from e

    forgive_missing_fixed_page(user_obj, paper_number, page_number)


def get_substitute_page_info(paper_number: int, page_number: int) -> dict[str, Any]:
    """Get information about the fixed page of the given paper/page.

    Returns a dict with keys "paper_number", "page_number", "version" and then
        "substitute_image_pk" and "kind". "Kind" is one of "IDPage", "QuestionPage", or "DNMPage"

    Raises:
        ValueError: When no fixed page at the given paper/page exists.
    """
    try:
        fixedpage_obj = FixedPage.objects.get(
            paper__paper_number=paper_number, page_number=page_number
        )
    except FixedPage.DoesNotExist as e:
        raise ValueError(
            f"Cannot find FixedPage of paper {paper_number} page {page_number}: {e}"
        ) from e
    version = fixedpage_obj.version
    substitute_image_pk = get_substitute_image(page_number, version).pk

    if isinstance(fixedpage_obj, DNMPage):
        kind = "DNMPage"
    elif isinstance(fixedpage_obj, IDPage):
        kind = "IDPage"
    else:  # must be a question page
        kind = "QuestionPage"

    return {
        "paper_number": paper_number,
        "page_number": page_number,
        "version": version,
        "substitute_image_pk": substitute_image_pk,
        "kind": kind,
    }


def get_list_of_all_missing_dnm_pages() -> list[dict[str, int]]:
    """Get list of missing do-not-mark pages from incomplete papers.

    Returns: A list of dicts with keys ``paper_number`` and ``page_number``.
    """
    incomplete_papers = ManageScanService.get_all_incomplete_papers()
    missing_dnm = []
    for paper_number, dat in incomplete_papers.items():
        for fp in dat["fixed"]:
            if fp["status"] == "missing" and fp["kind"] == "DNMPage":
                missing_dnm.append(
                    {"paper_number": paper_number, "page_number": fp["page_number"]}
                )
    return missing_dnm

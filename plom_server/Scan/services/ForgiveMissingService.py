# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald

import hashlib
from io import BytesIO
from typing import Any

import pymupdf

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User

from Papers.models import (
    Bundle,
    Image,
    FixedPage,
    DiscardPage,
    IDPage,
    DNMPage,
)
from Papers.services import SpecificationService
from Preparation.services import SourceService
from ..services import ManageDiscardService, ManageScanService

# The name of the bundle of substitute pages to use
# when student's paper is missing pages
# We need this since all images belong to bundles
#
system_substitute_images_bundle_name = "__system_substitute_pages_bundle__"
font_size_for_forgiven_blurb = 36
page_not_submitted_text = "Page Not Submitted"


def _get_or_create_substitute_pages_bundle() -> Bundle:
    """Create (if needed) and return the system substitute pages bundle database object.

    Warning: rather slow, and currently (2025-03) this is called in an async way.
    So we make it durable to prevent more than one from running.
    """
    with transaction.atomic(durable=True):
        try:
            print("trying to make the subs bundle...")
            bundle_obj = Bundle.objects.create(
                name=system_substitute_images_bundle_name,
                hash="bundle_for_substitute_pages",
                _is_singleton=True,
            )
            do_make_bundle = True
        except IntegrityError:
            do_make_bundle = False
        if do_make_bundle:
            # ok, so we're making it, do all the images
            print(f"Starting a new subs bundle: {bundle_obj}")
            assert bundle_obj.image_set.count() == 0
            _create_bundle_of_substitute_pages(bundle_obj)
        # if we're *not* making a bundle (b/c it already exists) then no
        # action is required; let the transaction expire.

    # either it exists or we just made it, either way get it again and return it
    existing_obj = Bundle.objects.get(name=system_substitute_images_bundle_name)
    print(f"returning bundle obj: {existing_obj}")
    return existing_obj


def _create_substitute_page_images_for_forgiveness_bundle() -> list[dict[str, Any]]:
    """Create all the substitute page pixmaps for missing pages.

    Returns:
        List of dicts of form {'page':page,
        'version': version,
        'name': suggested image filename,
        'bytes': the bytes of the image saved as png
        } - one such dict for each page/version.
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


def _create_bundle_of_substitute_pages(bundle_obj: Bundle) -> None:
    """Create the substitute images bundle and populate it with images.

    The system substitute image bundle is populated
    with a substitute image for each page/version of the assessment. If the
    assessment has n_pages pages, then the substitute image for page p of version v
    is created at bundle-order v*n_pages + p.
    """
    n_pages = SpecificationService.get_n_pages()
    image_list = _create_substitute_page_images_for_forgiveness_bundle()
    if True:
        for n, img_dat in enumerate(image_list):
            bundle_order = img_dat["version"] * n_pages + img_dat["page_number"]
            image_name = img_dat["name"]
            image_bytes = img_dat["bytes"]
            image_hash = hashlib.sha256(image_bytes).hexdigest()
            image_file = File(BytesIO(image_bytes), name=image_name)
            Image.objects.create(
                bundle=bundle_obj,
                bundle_order=bundle_order,
                original_name=image_name,
                image_file=image_file,
                hash=image_hash,
                parsed_qr={},
                rotation=0,
            )


def have_substitute_images_been_created() -> bool:
    """Test if there are any images in the system substitute image bundle."""
    bundle_obj = _get_or_create_substitute_pages_bundle()
    return bundle_obj.image_set.count() > 0


def get_substitute_image(page_number: int, version: int) -> Image:
    """Return the substitute Image-object for the given page/version."""
    print("calling get_or_create...")
    bundle_obj = _get_or_create_substitute_pages_bundle()
    print("back from get_or_create")
    # bundle_order = version*number of pages + page_number
    n_pages = SpecificationService.get_n_pages()  # 1-indexed
    bundle_order = n_pages * version + page_number
    return Image.objects.get(bundle=bundle_obj, bundle_order=bundle_order)


def get_substitute_image_from_pk(image_pk: int) -> Image:
    """Return the Image object with the given pk."""
    return Image.objects.get(pk=image_pk)


def _delete_substitute_images():
    """Delete all the images from the system substitute image bundle."""
    with transaction.atomic(durable=True):
        try:
            bundle_obj = Bundle.objects.get(name=system_substitute_images_bundle_name)
        except ObjectDoesNotExist:
            # nothing needs done if no bundle
            return
        for X in bundle_obj.image_set.all():
            X.delete()
        bundle_obj.delete()


def forgive_missing_fixed_page(
    user_obj: User, paper_number: int, page_number: int
) -> None:
    """Replace the given fixed page with a substitute page image.

    Args:
        user_obj: the user-object who is doing the forgiving.
        paper_number: the paper
        page_number: the page from the paper that is missing.

    Raises:
        ObjectDoesNotExist: If the fixed-page of the given paper/page does not exist.
        ValueError: If the paper/page has actually been scanned and the corresponding fixed-page object has an image.

    """
    try:
        fixedpage_obj = FixedPage.objects.get(
            paper__paper_number=paper_number, page_number=page_number
        )
    except ObjectDoesNotExist:
        raise ValueError(
            f"Cannot find the fixed page of paper {paper_number} page {page_number}"
        )
    if fixedpage_obj.image:
        raise ValueError(
            f"Paper {paper_number} page {page_number} already has an image - there is nothing to forgive!"
        )
    image_obj = get_substitute_image(page_number, fixedpage_obj.version)
    # create a discard page and then move it into place via assign_discard_page_to_fixed_page.
    discardpage_obj = DiscardPage.objects.create(
        image=image_obj,
        discard_reason=f"System created page to susbstitue for paper {paper_number} page {page_number}",
    )
    ManageDiscardService().assign_discard_page_to_fixed_page(
        user_obj, discardpage_obj.pk, paper_number, page_number
    )


def forgive_missing_fixed_page_cmd(
    username: str, paper_number: int, page_number: int
) -> None:
    """Simple wrapper around forgive_missing_fixed_page.

    Raises:
        ObjectDoesNotExist: when the given username does not exist or has wrong permissions.
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
        ObjectDoesNotExist: When no fixed page at the given paper/page exists.
    """
    try:
        fixedpage_obj = FixedPage.objects.get(
            paper__paper_number=paper_number, page_number=page_number
        )
    except ObjectDoesNotExist as e:
        raise ValueError(
            f"Cannot find the fixed page of paper {paper_number} page {page_number}"
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

    Returns: A list of dict of the form {'paper_number':foo, "page_number": bah}
    """
    incomplete_papers = ManageScanService().get_all_incomplete_test_papers()
    missing_dnm = []
    for paper_number, dat in incomplete_papers.items():
        for fp in dat["fixed"]:
            if fp["status"] == "missing" and fp["kind"] == "DNMPage":
                missing_dnm.append(
                    {"paper_number": paper_number, "page_number": fp["page_number"]}
                )
    return missing_dnm

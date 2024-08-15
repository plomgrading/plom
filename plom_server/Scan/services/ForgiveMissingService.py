# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations
import fitz
import hashlib
from io import BytesIO

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db import transaction
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
from Progress.services import ManageDiscardService

# The name of the bundle to use for these missing pages
# We need this since all images belong to bundles
#
system_substitute_images_bundle_name = "__system_subsitute_pages_bundle__"
font_size_for_forgiven_blurb = 36
page_not_submitted_text = "Page Not Submitted"


@transaction.atomic
def _get_or_create_missing_pages_bundle() -> Bundle:
    try:
        bundle_obj = Bundle.objects.get(name=system_substitute_images_bundle_name)
    except ObjectDoesNotExist:
        bundle_obj = Bundle.objects.create(
            name=system_substitute_images_bundle_name,
            hash="bundle_for_missing_pages",
        )
    return bundle_obj


def _create_missing_page_images_for_forgiveness_bundle():
    version_list = SpecificationService.get_list_of_versions()
    page_list = SpecificationService.get_list_of_pages()  # 1-indexed
    image_list = []
    for v in version_list:
        doc = fitz.Document(stream=SourceService.get_source_as_bytes(v))
        for pg in page_list:
            the_page = doc[pg - 1]  # 0-indexed
            the_rect = the_page.rect
            pns_length = fitz.get_text_length(
                page_not_submitted_text, fontsize=font_size_for_forgiven_blurb
            )
            text_start = (
                (the_rect.width - pns_length) // 2,
                the_rect.height // 10 + font_size_for_forgiven_blurb,
            )
            text_box = fitz.Rect(
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
            text_box = fitz.Rect(
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
            text_blob_length = fitz.get_text_length(
                text_blob, fontsize=font_size_for_forgiven_blurb
            )
            text_start = (
                (the_rect.width - text_blob_length) // 2,
                the_rect.height // 2,
            )
            text_box = fitz.Rect(
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


def create_bundle_of_substitute_pages():
    n_pages = SpecificationService.get_n_pages()
    bundle_obj = _get_or_create_missing_pages_bundle()
    if bundle_obj.image_set.count() > 0:
        print("Already images here")
        return
    else:
        image_list = _create_missing_page_images_for_forgiveness_bundle()
    with transaction.atomic():
        for n, img_dat in enumerate(image_list):
            bundle_order = img_dat["version"] * n_pages + img_dat["page_number"]
            print(f"Creating image at {bundle_order}")
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
    bundle_obj = _get_or_create_missing_pages_bundle()
    return bundle_obj.image_set.count() > 0


@transaction.atomic()
def get_substitute_image(page_number: int, version: int) -> Image:
    bundle_obj = _get_or_create_missing_pages_bundle()
    if bundle_obj.image_set.count() == 0:
        create_bundle_of_substitute_pages()
    # bundle_order = version*number of pages + page_number
    n_pages = SpecificationService.get_n_pages()  # 1-indexed
    bundle_order = n_pages * version + page_number
    return Image.objects.get(bundle=bundle_obj, bundle_order=bundle_order)


@transaction.atomic()
def get_substitute_image_from_pk(image_pk: int) -> Image:
    return Image.objects.get(pk=image_pk)


@transaction.atomic()
def _delete_substitute_images():
    bundle_obj = _get_or_create_missing_pages_bundle()
    for X in bundle_obj.image_set.all():
        X.delete()


def forgive_missing_fixed_page(user_obj: User, paper_number: int, page_number: int):
    try:
        fpage_obj = FixedPage.objects.get(
            paper__paper_number=paper_number, page_number=page_number
        )
    except ObjectDoesNotExist:
        raise ValueError(
            f"Cannot find the fixed page of paper {paper_number} page {page_number}"
        )
    if fpage_obj.image:
        raise ValueError(
            f"Paper {paper_number} page {page_number} already has an image - there is nothing to forgive!"
        )
    image_obj = get_substitute_image(page_number, fpage_obj.version)
    # create a discard page and then move it into place via assign_discard_image_to_fixed_page.
    DiscardPage.objects.create(
        image=image_obj,
        discard_reason=f"System created page to susbstitue for paper {paper_number} page {page_number}",
    )
    ManageDiscardService().assign_discard_image_to_fixed_page(
        user_obj, image_obj.pk, paper_number, page_number
    )


def forgive_missing_fixed_page_cmd(username: str, paper_number: int, page_number: int):
    try:
        user_obj = User.objects.get(username__iexact=username, groups__name="manager")
    except ObjectDoesNotExist as e:
        raise ValueError(
            f"User '{username}' does not exist or has wrong permissions."
        ) from e

    forgive_missing_fixed_page(user_obj, paper_number, page_number)


def get_substitute_page_info(paper_number, page_number):
    try:
        fpage_obj = FixedPage.objects.get(
            paper__paper_number=paper_number, page_number=page_number
        )
    except ObjectDoesNotExist:
        raise ValueError(
            f"Cannot find the fixed page of paper {paper_number} page {page_number}"
        )
    version = fpage_obj.version
    substitute_image_pk = get_substitute_image(page_number, version).pk

    if isinstance(fpage_obj, DNMPage):
        kind = "DNMPage"
    elif isinstance(fpage_obj, IDPage):
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

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

from datetime import datetime
import hashlib
import pathlib

import fitz
from fitz import FileDataError

from django.utils import timezone
from django import forms
from django.forms import ValidationError
from django.utils.text import slugify
from django.conf import settings

from .services import ScanService


class BundleUploadForm(forms.Form):
    """Django form for upload of a bundle PDF."""

    pdf = forms.FileField(
        allow_empty_file=False,
        label="",
        widget=forms.FileInput(attrs={"accept": "application/pdf"}),
    )

    def clean(self):
        data = self.cleaned_data
        pdf = data["pdf"]

        # TODO: set a request size limit in production
        if pdf.size > settings.MAX_BUNDLE_SIZE:
            readable_file_size = settings.MAX_BUNDLE_SIZE / 1e9
            raise ValidationError(f"Bundle size limit is {readable_file_size} GB.")

        # correct format, readable by fitz, not a duplicate?
        try:
            file_bytes = pdf.read()
            pdf_doc = fitz.open(stream=file_bytes)
            if "PDF" not in pdf_doc.metadata["format"]:
                raise ValidationError("File is not a valid PDF.")

            # TODO: Should we prevent uploading duplicate bundles or warn them?
            hashed = hashlib.sha256(file_bytes).hexdigest()
            scanner = ScanService()
            if scanner.check_for_duplicate_hash(hashed):
                raise ValidationError("Bundle was already uploaded.")

            # get slug
            filename_stem = pathlib.Path(str(pdf)).stem
            slug = slugify(filename_stem)

            data.update(
                {
                    "number_of_pages": pdf_doc.page_count,
                    "slug": slug,
                    "time_uploaded": timezone.now(),
                    "sha256": hashed,
                }
            )
            return data
        except (FileDataError, KeyError):
            raise ValidationError("Unable to open file.")


class FlagImageForm(forms.Form):
    """A form to flag the images with error to the manager."""

    comment = forms.CharField(
        label="Comment",
        widget=forms.Textarea(
            attrs={
                "class": "comment-input",
                "placeholder": "Comment to manager about this page (optional)",
                "name": "comment",
                "style": "display: block; width: 100%; height: 100px; border-radius: 0.375rem; margin-bottom: 4px;",
            }
        ),
        required=False,
    )


class ReplaceImageForm(forms.Form):
    """Replace an error page image form."""

    single_pdf = forms.FileField(
        allow_empty_file=False,
        max_length=100,
        label="",
        widget=forms.FileInput(attrs={"accept": "application/pdf"}),
    )

    def clean(self):
        data = self.cleaned_data
        single_pdf = data["single_pdf"]

        # set a file size?
        # if single_pdf.size > settings.MAX_FILE_SIZE:
        #     readable_single_file_size = settings.MAXFILE_SIZE / 1e6
        #     raise ValidationError(f"File size limit is {readable_single_file_size} MB.")

        try:
            scanner = ScanService()
            file_bytes = single_pdf.read()
            pdf_doc = fitz.open(stream=file_bytes)

            # make sure it is correct format
            if "PDF" not in pdf_doc.metadata["format"]:
                raise ValidationError("File is not a valid PDF.")

            # make sure only 1 pdf page
            if pdf_doc.page_count > 1:
                raise ValidationError("Only upload a single page pdf file.")

            # turn that pdf file into page image
            timestamp = datetime.timestamp(timezone.now())
            file_name = f"{timestamp}.pdf"
            replace_dir = settings.MEDIA_ROOT / "replace_pages"
            replace_dir.mkdir(exist_ok=True)
            save_as_pdf = replace_dir / "pdfs"
            save_as_pdf.mkdir(exist_ok=True)
            with open(save_as_pdf / file_name, "w") as f:
                pdf_doc.save(f)

            save_dir = replace_dir / "images"
            save_dir.mkdir(exist_ok=True)

            uploaded_pdf_file = fitz.Document(save_as_pdf / file_name)
            transform = fitz.Matrix(4, 4)
            pixmap = uploaded_pdf_file[0].get_pixmap(matrix=transform)

            # check uploaded image hash and save image as hash
            uploaded_image_hash = hashlib.sha256(pixmap.tobytes()).hexdigest()
            save_as_image = save_dir / f"{uploaded_image_hash}.png"
            all_image_hash_list = scanner.get_all_staging_image_hash()
            for image_hash in all_image_hash_list:
                if str(uploaded_image_hash) == str(image_hash["image_hash"]):
                    pathlib.Path.unlink(save_as_pdf / file_name)
                    pathlib.Path.unlink(save_as_image)
                    raise ValidationError("This page already uploaded.")
                else:
                    # save image file name as image hash
                    pixmap.save(save_as_image)

            # removes the file
            pathlib.Path.unlink(save_as_pdf / file_name)
            pathlib.Path.unlink(save_as_image)

            data.update(
                {
                    "pdf_doc": pdf_doc,
                    "time_uploaded": timestamp,
                    "uploaded_image_hash": uploaded_image_hash,
                }
            )
            return data

        except (FileDataError, KeyError):
            raise ValidationError("Unable to open file.")

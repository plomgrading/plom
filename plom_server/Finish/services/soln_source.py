# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

import hashlib
import io

import pymupdf as fitz

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db import transaction

from plom_server.Papers.services import SpecificationService, SolnSpecService
from plom_server.Papers.models import SolnSpecQuestion

from ..models import SolutionSourcePDF, SolutionImage


class SolnSourceService:
    def is_there_a_solution_pdf(self, version: int) -> bool:
        """Returns true if a solution pdf of given version has been uploaded."""
        return SolutionSourcePDF.objects.filter(version=version).exists()

    def are_there_any_solution_pdf(self) -> bool:
        """Returns true if any solution pdf have been uploaded."""
        return SolutionSourcePDF.objects.exists()

    def get_number_of_solution_pdf(self) -> int:
        """Returns number of uploaded solution pdf."""
        return SolutionSourcePDF.objects.count()

    def are_all_solution_pdf_present(self) -> bool:
        """Returns true if all required solution pdf have been uploaded."""
        return (
            SolutionSourcePDF.objects.all().count()
            == SpecificationService.get_n_versions()
        )

    def get_solution_pdf_hashes(self) -> dict[int, None | str]:
        """Returns dict of hash of each uploaded solution pdf, or Nones if pdf missing."""
        soln_pdfs: dict[int, None | str] = {
            v: None for v in SpecificationService.get_list_of_versions()
        }
        for spdf in SolutionSourcePDF.objects.all():
            soln_pdfs[spdf.version] = spdf.pdf_hash
        return soln_pdfs

    @transaction.atomic
    def get_list_of_sources(self) -> dict[int, None | tuple[str, str]]:
        """Return a dict of all versions, uploaded or not."""
        status: dict[int, None | tuple[str, str]] = {
            v: None for v in SpecificationService.get_list_of_versions()
        }
        for soln_pdf_obj in SolutionSourcePDF.objects.all():
            status[soln_pdf_obj.version] = (
                soln_pdf_obj.source_pdf.url,
                soln_pdf_obj.pdf_hash,
            )
        return status

    @staticmethod
    def remove_solution_pdf(version: int):
        """Remove solution pdf and associated images for the given version."""
        with transaction.atomic(durable=True):
            try:
                soln_source_obj = SolutionSourcePDF.objects.get(version=version)
            except ObjectDoesNotExist:
                raise ValueError(f"There is no solution pdf for version {version}")
            soln_source_obj.delete()  # delete the db row
            # remove any associated images, first by deleting their db rows
            img_objs = SolutionImage.objects.filter(version=version)
            for img_obj in img_objs:
                img_obj.delete()

        # now that we're sure the database has been updated (by the atomic durable)
        # we can safely delete the files.  If the power went out *right now*, the
        # database would be fine and we'd have dangling files on disc.
        if soln_source_obj.source_pdf:
            soln_source_obj.source_pdf.delete()  # delete the underlying file
        for img_obj in img_objs:
            if img_obj.image:
                img_obj.image.delete()  # delete the underlying file

    @classmethod
    def remove_all_solution_pdf(cls):
        """Remove all solution pdfs and associated images."""
        for obj in SolutionSourcePDF.objects.all():
            cls.remove_solution_pdf(obj.version)

    def get_soln_pdf_for_download(self, version: int) -> io.BytesIO:
        """Return bytes of solution pdf for given version."""
        if version not in SpecificationService.get_list_of_versions():
            raise ValueError(f"Version {version} is out of range")
        try:
            soln_pdf_obj = SolutionSourcePDF.objects.get(version=version)
        except ObjectDoesNotExist:
            raise ValueError(
                f"The solution source pdf for version {version} has not yet been uploaded."
            )
        return io.BytesIO(soln_pdf_obj.source_pdf.read())

    @transaction.atomic
    def take_solution_source_pdf_from_upload(
        self, version: int, in_memory_file
    ) -> None:
        """Take the given solution source pdf and save it to the DB."""
        if version not in SpecificationService.get_list_of_versions():
            raise ValueError(f"Version {version} is out of range")
        if not SolnSpecService.is_there_a_soln_spec():
            raise ValueError("Cannot upload pdf until there is a solution spec")
        if SolutionSourcePDF.objects.filter(version=version).exists():
            raise ValueError(
                f"A pdf for solution version {version} has already been uploaded"
            )

        # read the file into here so we can do some correctness checks before saving it.
        file_bytes = in_memory_file.read()

        with fitz.open(stream=file_bytes) as doc:
            if len(doc) != SolnSpecService.get_n_pages():
                raise ValueError(
                    f"Solution pdf does has {len(doc)} pages - needs {SolnSpecService.get_n_pages()}."
                )

            doc_hash = hashlib.sha256(file_bytes).hexdigest()
            # check if there is an existing solution with that hash
            if SolutionSourcePDF.objects.filter(pdf_hash=doc_hash).exists():
                raise ValueError(
                    f"Another solution pdf with hash {doc_hash} has already been uploaded."
                )
            # create the DB entry
            SolutionSourcePDF.objects.create(
                version=version,
                source_pdf=File(io.BytesIO(file_bytes), name=f"solution{version}.pdf"),
                pdf_hash=doc_hash,
            )
            # We need to create solution images for display in the client
            # Assembly of solutions for each paper will use the source pdfs, not these images.
            self._create_solution_images(version, doc)

    def _create_solution_images(self, version: int, doc: fitz.Document) -> None:
        """Create one solution image for each question of the given version, for client.

        Images are extracted at 150 DPI.
        """
        # for each solution, glue the corresponding page images into a single row.
        for sqs_obj in SolnSpecQuestion.objects.all():
            # see https://pymupdf.readthedocs.io/en/latest/recipes-images.html#how-to-use-pixmaps-gluing-images
            # get an image for each page - pymupdf pages are 0-indexed.
            pix_list = [doc[pg - 1].get_pixmap(dpi=150) for pg in sqs_obj.pages]
            total_w = sum([X.width for X in pix_list])
            max_h = max([X.height for X in pix_list])
            # creage a dest image on which to tile these images - with given max height and total width.
            soln_img = fitz.Pixmap(
                pix_list[0].colorspace, (0, 0, total_w, max_h), pix_list[0].alpha
            )
            # concat the images together into the dest image.
            starting_x = 0
            for pix in pix_list:
                pix.set_origin(starting_x, 0)
                soln_img.copy(pix, pix.irect)
                starting_x += pix.width
            # now save the result into the DB.
            SolutionImage.objects.create(
                version=version,
                question_index=sqs_obj.question_index,
                image=File(
                    io.BytesIO(soln_img.tobytes()),
                    name=f"soln_{version}_{sqs_obj.question_index}.png",
                ),
            )

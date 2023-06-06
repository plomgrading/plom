# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Colin B. Macdonald

import pathlib
from warnings import warn

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from Scan.services.image_process import PageImageProcessor
from Papers.models import Image, IDPage, Paper


class IDReaderService:
    """Functions for reading and processing ID pages of pushed papers."""

    @transaction.atomic
    def get_id_box_cmd(self, box, *, dur=None):
        """Extract the id box, or really any rectangular part of the id page, rotation corrected.

        Args:
            box (None/list): the box to extract or a default is empty/None.

        Keyword Args:
            dur (None/pathlib.Path): what directory to save to, or choose
                a internal default if omitted.

        Returns:
            None
        """
        if not dur:
            id_box_folder = settings.MEDIA_ROOT / "id_box_images"
        else:
            id_box_folder = pathlib.Path(dur)
        if not box:
            box = (0.28, 0.58, 0.09, 0.91)
        id_box_folder.mkdir(exist_ok=True)

        pipr = PageImageProcessor()
        id_pages = IDPage.objects.all()

        for id_img in id_pages:
            if id_img.image:
                img_path = id_img.image.image_file.path
                orientation = id_img.image.rotation
                qr_data = id_img.image.parsed_qr
                if len(qr_data) != 3:
                    warn(
                        "Fewer than 3 QR codes found, "
                        f"cannot extract ID box from paper {id_img.paper.paper_number}."
                    )
                    continue
                id_box = pipr.extract_rect_region(img_path, orientation, qr_data, *box)
                id_box.save(
                    id_box_folder / f"id_box_{id_img.paper.paper_number:04}.png"
                )

    @transaction.atomic
    def get_id_digits_per_paper_cmd(self, *, dur=None):
        """Extract the digits for each paper's id box, organized on-disk in paper_num-labelled dirs.

        Keyword Args:
            dur (None/pathlib.Path): what directory to save to, or choose
                a internal default if omitted.

        Returns:
            None
        """
        if not dur:
            id_box_folder = settings.MEDIA_ROOT / "id_box_images"
        else:
            id_box_folder = pathlib.Path(dur)
        id_box_folder.mkdir(exist_ok=True)

        pipr = PageImageProcessor()
        id_pages = IDPage.objects.all()

        for id_img in id_pages:
            if id_img.image:
                img_path = id_img.image.image_file.path
                orientation = id_img.image.rotation
                qr_data = id_img.image.parsed_qr
                if len(qr_data) != 3:
                    warn(
                        "Fewer than 3 QR codes found, "
                        f"cannot extract ID box from paper {id_img.paper.paper_number}."
                    )
                    continue
                digit_folder = id_box_folder / f"paper{id_img.paper.paper_number:04}"
                digit_folder.mkdir(exist_ok=True)
                for i in range(0, 8):
                    digit_box = pipr.extract_rect_region(img_path, orientation, qr_data)
                    digit_box.save(
                        digit_folder / f"digit{i}.png"
                    )

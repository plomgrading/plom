# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from Papers.models import (
    FixedPage,
    MobilePage,
    Paper,
    Image,
    Bundle,
    IDPage,
    DNMPage,
    QuestionPage,
)

from Identify.models import PaperIDTask
from Mark.models import MarkingTask


class ManageDiscardService:
    """Functions for overseeing discarding pushed images."""

    def discard_pushed_image(self, user_obj, image_pk, *, dry_run=True):
        try:
            img = Image.objects.get(pk=image_pk)
        except ObjectDoesNotExist:
            raise ValueError(f"Cannot find pushed image with pk {image_pk}")
        # now check what sort of page image is attached to

        try:
            img.discardpage
            return f"Image {image_pk} is already a discard page - no action taken"
        except ObjectDoesNotExist:
            pass

        if img.mobilepage_set.exists():
            mp_info = []
            for mp in img.mobilepage_set.all():
                mp_info.append(("M", mp.paper.paper_number, mp.question_number))

            return f"Image {image_pk} is attached to mobilepages - {mp_info}"

        if img.fixedpage_set.exists():
            fp_info = []
            for fp in img.fixedpage_set.all():
                if isinstance(fp, IDPage):
                    fp_info.append(("ID", fp.paper.paper_number, fp.page_number))
                if isinstance(fp, DNMPage):
                    fp_info.append(("DNM", fp.paper.paper_number, fp.page_number))
                if isinstance(fp, QuestionPage):
                    fp_info.append(
                        ("Q", fp.paper.paper_number, fp.page_number, fp.question_number)
                    )

            print(f"Image {image_pk} is attached to fixedpages - {fp_info}")

        raise ValueError("Cannot work out what type of page image is attached to")

    def discard_pushed_fixed_page(
        self, user_obj, paper_obj, fixedpage_number, *, dry_run=True
    ):
        ret = [fp for fp in paper_obj.fixedpage_set.all()]
        return ret

    def discard_pushed_mobile_page(
        self, user_obj, paper_obj, mobile_number, *, dry_run=True
    ):
        ret = [fp for fp in paper_obj.fixedpage_set.all()]
        return ret

    def pushed_pages_associated_with_paper(self, paper_obj):
        return {
            "fixed": [fp for fp in paper_obj.fixedpage_set.all()],
            "mobile": [mp for mp in paper_obj.mobilepage_set.all()],
        }

    def discard_pushed_page_cmd(
        self,
        username,
        paper_number,
        *,
        image_pk=None,
        fixedpage_number=None,
        mobilepage_number=None,
        dry_run=True,
    ):

        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="manager"
            )
        except ObjectDoesNotExist:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions."
            )
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except ObjectDoesNotExist:
            raise ValueError(f"Paper {paper_number} is not in the database.")

        if image_pk:
            return self.discard_pushed_image(
                user_obj, image_pk, dry_run=dry_run
            )
        elif fixedpage_number:
            return self.discard_pushed_fixed_page(
                user_obj, paper_obj, fixedpage_number, dry_run=dry_run
            )
        elif mobilepage_number:
            return self.discard_pushed_mobile_page(
                user_obj, paper_obj, mobilepage_number, dry_run=dry_run
            )
        else:
            return self.pushed_pages_associated_with_paper(paper_obj)

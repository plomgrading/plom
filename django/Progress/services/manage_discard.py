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
)


class ManageDiscardService:
    """Functions for overseeing discarding pushed images."""

    def discard_pushed_fixed_page(self, user_obj, paper_obj):
        ret = [fp for fp in paper_obj.fixedpage_set.all()]
        return ret

    def discard_pushed_page_cmd(self, username, paper_number):
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="manager"
            )
        except ObjectDoesNotExist:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            )
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except ObjectDoesNotExist:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions!"
            )

        return self.discard_pushed_fixed_page(user_obj, paper_obj)

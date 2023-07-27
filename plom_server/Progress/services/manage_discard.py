# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from Papers.models import (
    FixedPage,
    MobilePage,
    IDPage,
    DNMPage,
    QuestionPage,
    DiscardPage,
)


class ManageDiscardService:
    """Functions for overseeing discarding pushed images."""

    @transaction.atomic
    def discard_dnm_page(self, user_obj: User, dnm_obj: DNMPage):
        DiscardPage.objects.create(
            image=dnm_obj.image,
            discard_reason=f"User {user_obj.username} discarded dnm paper {dnm_obj.paper.paper_number} page {dnm_obj.page_number}",
        )
        # Set the original dnm page to have no image, but **DO NOT** delete the DNM page
        dnm_obj.image = None
        dnm_obj.save()
        # Notice that no tasks need be invalidated since this is a DNM page.

    @transaction.atomic
    def discard_id_page(self, user_obj: User, idpage_obj: IDPage):
        raise NotImplementedError("Need to set up ID task invalidation")

        DiscardPage.objects.create(
            image=idpage_obj.image,
            discard_reason=f"User {user_obj.username} discarded id paper {idpage_obj.paper.paper_number} page {idpage_obj.page_number}",
        )
        # set the associated IDing task to "OUT_OF_DATE"
        # >>> TODO <<<

        # Set the original id page to have no image, but **DO NOT** delete the idpage
        idpage_obj.image = None
        idpage_obj.save()

    @transaction.atomic
    def discard_question_page(self, user_obj: User, qpage_obj: QuestionPage):
        raise NotImplementedError("Need to set up Marking task invalidation")

        DiscardPage.objects.create(
            image=qpage_obj.image,
            discard_reason=f"User {user_obj.username} discarded paper {qpage_obj.paper.paper_number} page {qpage_obj.page_number} question {qpage_obj.question_number}.",
        )
        # set the associated IDing task to "OUT_OF_DATE"
        # >>> TODO <<<

        # Set the original question page to have no image, but **DO NOT** delete the question page
        qpage_obj.image = None
        qpage_obj.save()

    @transaction.atomic
    def discard_mobile_page(self, user_obj: User, mpage_obj: MobilePage):
        raise NotImplementedError("Need to set up Marking task invalidation")

        # note that a single mobile page is attached to an image that
        # might be associated with multiple questions. Accordingly
        # when we discard this mobile-page we also discard any other
        # mobile pages associated with this image **and** also flag
        # the marking tasks associated with those mobile pages as 'out
        # of date'

        DiscardPage.objects.create(
            image=mpage_obj.image,
            discard_reason=f"User {user_obj.username} discarded mobile paper {mpage_obj.paper.paper_number} question {mpage_obj.question_number}.",
        )

        # find all the mobile pages associated with this image
        # set the associated marking tasks to "OUT_OF_DATE"
        # >>> TODO <<<
        # and now delete each of those mobile pages
        mpage_obj.delete()

    def discard_pushed_fixed_page(self, user_obj, fixedpage_pk, *, dry_run=True) -> str:
        """Discard a fixed page, such an ID page, DNM page or Question page.

        Args:
            TODO

        Keyword Args:
            dry_run: really do it or just pretend?

        Returns:
            A status message about what happened (or, if ``dry_run`` is True,
            what would be attempted).

        Raises:
            ValueError: no such page, no image attached to page, unexpectedly
                unknown page type, maybe other cases.
        """
        try:
            fp_obj = FixedPage.objects.get(pk=fixedpage_pk)
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"A fixed page with pk {fixedpage_pk} does not exist"
            ) from e

        if fp_obj.image is None:
            raise ValueError(
                f"There is no image attached to fixed page {fixedpage_pk} "
                f"(which is paper {fp_obj.paper.paper_number} page {fp_obj.page_number})"
            )

        if isinstance(fp_obj, DNMPage):
            if dry_run:
                return f"DRY-RUN: would drop DNMPage paper {fp_obj.paper.paper_number} page {fp_obj.page_number}"
            self.discard_dnm_page(user_obj, fp_obj)
            return f"Have dropped DNMPage paper {fp_obj.paper.paper_number} page {fp_obj.page_number}"
        elif isinstance(fp_obj, IDPage):
            if dry_run:
                return f"DRY-RUN: would drop IDPage paper {fp_obj.paper.paper_number} page {fp_obj.page_number}"
            self.discard_id_page(user_obj, fp_obj)
            return f"Have dropped IDPage paper= {fp_obj.paper.paper_number} page {fp_obj.page_number}. The associated ID-task has been flagged as 'out of date'"
        elif isinstance(fp_obj, QuestionPage):
            if dry_run:
                return f"DRY-RUN: would drop QuestionPage for paper {fp_obj.paper.paper_number} page {fp_obj.page_number} question {fp_obj.question_number}"
            self.discard_question_page(user_obj, fp_obj)
            return f"Have dropped QuestionPage for paper {fp_obj.paper.paper_number} page {fp_obj.page_number} question {fp_obj.question_number}. The associated marking task has been flagged as 'out of date'"

        else:
            raise ValueError("Cannot determine what sort of fixed-page this is")

    def discard_pushed_mobile_page(self, user_obj, mobilepage_pk, *, dry_run=True):
        try:
            mp_obj = MobilePage.objects.get(pk=mobilepage_pk)
        except ObjectDoesNotExist:
            raise ValueError(f"A mobile page with pk {mobilepage_pk} does not exist")

        if dry_run:
            return f"DRY-RUN: would drop a MobilePage for paper {mp_obj.paper.paper_number} question {mp_obj.question_number}"
        else:
            self.discard_mobile_page(user_obj, mp_obj)
            return f"Have dropped a Mobilepage for paper {mp_obj.paper.paper_number} question {mp_obj.question_number} and flagged the associated marking task as 'out of date'"

    def discard_pushed_page_cmd(
        self,
        username,
        *,
        fixedpage_pk=None,
        mobilepage_pk=None,
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

        if fixedpage_pk:
            return self.discard_pushed_fixed_page(
                user_obj, fixedpage_pk, dry_run=dry_run
            )
        elif mobilepage_pk:
            return self.discard_pushed_mobile_page(
                user_obj, mobilepage_pk, dry_run=dry_run
            )
        else:
            raise ValueError("Command needs a pk for a fixedpage or mobilepage")

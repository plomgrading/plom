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
from Identify.services import IdentifyTaskService
from Mark.services import MarkingTaskService


class ManageDiscardService:
    """Functions for overseeing discarding pushed images."""

    @transaction.atomic
    def _discard_dnm_page(self, user_obj: User, dnm_obj: DNMPage) -> None:
        DiscardPage.objects.create(
            image=dnm_obj.image,
            discard_reason=(
                f"User {user_obj.username} discarded DNM page: "
                f"page {dnm_obj.paper.paper_number} page {dnm_obj.page_number}"
            ),
        )
        # Set the original dnm page to have no image, but **DO NOT** delete the DNM page
        dnm_obj.image = None
        dnm_obj.save()
        # Notice that no tasks need be invalidated since this is a DNM page.

    @transaction.atomic
    def _discard_id_page(self, user_obj: User, idpage_obj: IDPage) -> None:
        DiscardPage.objects.create(
            image=idpage_obj.image,
            discard_reason=(
                f"User {user_obj.username} discarded ID page: "
                f"page {idpage_obj.paper.paper_number} page {idpage_obj.page_number}"
            ),
        )
        # Set the original id page to have no image, but **DO NOT** delete the idpage
        idpage_obj.image = None
        idpage_obj.save()

        # now set the associated id-task to out of date.
        IdentifyTaskService().set_paper_idtask_outdated(idpage_obj.paper.paper_number)
        # notice that since there is only a single ID page we cannot
        # automatically create a new id-task, we need a new page to be uploaded.

    @transaction.atomic
    def _discard_question_page(self, user_obj: User, qpage_obj: QuestionPage) -> None:
        raise NotImplementedError("Need to set up Marking task invalidation")

        DiscardPage.objects.create(
            image=qpage_obj.image,
            discard_reason=(
                f"User {user_obj.username} discarded paper "
                f"{qpage_obj.paper.paper_number} page {qpage_obj.page_number} "
                f"question {qpage_obj.question_number}."
            ),
        )
        # set the associated Markinging task to "OUT_OF_DATE"
        MarkingTaskService().set_paper_marking_task_outdated(
            qpage_obj.paper.paper_number, qpage_obj.question_number
        )
        # TODO
        # Try to make a new marking task
        # TODO

        # Set the original question page to have no image, but **DO NOT** delete the question page
        qpage_obj.image = None
        qpage_obj.save()

    @transaction.atomic
    def _discard_mobile_page(self, user_obj: User, mpage_obj: MobilePage) -> None:
        raise NotImplementedError("Need to set up Marking task invalidation")

        # note that a single mobile page is attached to an image that
        # might be associated with multiple questions. Accordingly
        # when we discard this mobile-page we also discard any other
        # mobile pages associated with this image **and** also flag
        # the marking tasks associated with those mobile pages as 'out
        # of date'

        img_to_disc = mpage_obj.image
        paper_number = mpage_obj.paper.paper_number

        DiscardPage.objects.create(
            image=img_to_disc,
            discard_reason=(
                f"User {user_obj.username} discarded mobile "
                f"paper {paper_number} "
                f"question {mpage_obj.question_number}."
            ),
        )

        # find all the mobile pages associated with this image
        # set the associated marking tasks to "OUT_OF_DATE"
        qn_to_outdate = [
            mpg.question_number for mpg in img_to_disc.mobilepage_set.all()
        ]
        # outdate the associated marking tasks
        for qn in qn_to_outdate:
            MarkingTaskService.set_paper_marking_task_outdated(paper_number, qn)
        # and now delete each of those mobile pages
        for mpg in img_to_disc.mobilepage_set.all():
            mpg.delete()
        # TODO
        # Now for each of the questions try to make a new marking task
        # TODO

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
            msg = f"DNMPage paper {fp_obj.paper.paper_number} page {fp_obj.page_number}"
            if dry_run:
                return "DRY-RUN: would drop " + msg
            self._discard_dnm_page(user_obj, fp_obj)
            return "Have dropped " + msg
        elif isinstance(fp_obj, IDPage):
            msg = f"IDPage paper {fp_obj.paper.paper_number} page {fp_obj.page_number}"
            if dry_run:
                return f"DRY-RUN: would drop {msg}"
            self._discard_id_page(user_obj, fp_obj)
            return (
                f"Have dropped {msg} and "
                "flagged the associated ID-task as 'out of date'"
            )
        elif isinstance(fp_obj, QuestionPage):
            msg = f"QuestionPage for paper {fp_obj.paper.paper_number} "
            f"page {fp_obj.page_number} question {fp_obj.question_number}"
            if dry_run:
                return f"DRY-RUN: would drop {msg}"
            self._discard_question_page(user_obj, fp_obj)
            return (
                f"Have dropped {msg} and "
                "flagged the associated marking task as 'out of date'"
            )
        else:
            raise ValueError("Cannot determine what sort of fixed-page this is")

    def discard_pushed_mobile_page(
        self, user_obj, mobilepage_pk, *, dry_run=True
    ) -> str:
        try:
            mp_obj = MobilePage.objects.get(pk=mobilepage_pk)
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"A mobile page with pk {mobilepage_pk} does not exist"
            ) from e

        msg = (
            f"a MobilePage for paper {mp_obj.paper.paper_number} "
            f"question {mp_obj.question_number}"
        )
        if dry_run:
            return f"DRY-RUN: would drop {msg}"
        self._discard_mobile_page(user_obj, mp_obj)
        return (
            f"Have dropped {msg} and "
            "flagged the associated marking task as 'out of date'"
        )

    def discard_pushed_page_cmd(
        self,
        username,
        *,
        fixedpage_pk=None,
        mobilepage_pk=None,
        dry_run=True,
    ) -> str:
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="manager"
            )
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions."
            ) from e

        if fixedpage_pk and mobilepage_pk:
            raise ValueError("You cannot specify both fixedpage AND mobilepage")
        elif fixedpage_pk:
            return self.discard_pushed_fixed_page(
                user_obj, fixedpage_pk, dry_run=dry_run
            )
        elif mobilepage_pk:
            return self.discard_pushed_mobile_page(
                user_obj, mobilepage_pk, dry_run=dry_run
            )
        else:
            raise ValueError("Command needs a pk for a fixedpage or mobilepage")

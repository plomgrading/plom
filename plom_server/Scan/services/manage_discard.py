# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from plom_server.Papers.models import (
    Bundle,
    Paper,
    FixedPage,
    MobilePage,
    DiscardPage,
    Image,
)
from plom_server.Identify.services import IdentifyTaskService
from plom_server.Mark.services import MarkingTaskService

from ..models import StagingBundle


class ManageDiscardService:
    """Functions for overseeing discarding pushed images."""

    @transaction.atomic
    def _discard_dnm_page(self, user_obj: User, dnm_obj: FixedPage) -> None:
        assert dnm_obj.page_type == FixedPage.DNMPAGE
        DiscardPage.objects.create(
            image=dnm_obj.image,
            discard_reason=(
                f"User {user_obj.username} discarded DNM page: "
                f"paper {dnm_obj.paper.paper_number} page {dnm_obj.page_number}"
            ),
        )
        # Set the original dnm page to have no image, but **DO NOT** delete the DNM page
        dnm_obj.image = None
        dnm_obj.save()
        # Notice that no tasks need be invalidated since this is a DNM page.

    @transaction.atomic
    def _discard_id_page(self, user_obj: User, idpage_obj: FixedPage) -> None:
        assert idpage_obj.page_type == FixedPage.IDPAGE
        DiscardPage.objects.create(
            image=idpage_obj.image,
            discard_reason=(
                f"User {user_obj.username} discarded ID page: "
                f"paper {idpage_obj.paper.paper_number} page {idpage_obj.page_number} "
                f"version {idpage_obj.version}"
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
    def _discard_question_page(self, user_obj: User, qpage_obj: FixedPage) -> None:
        assert qpage_obj.page_type == FixedPage.QUESTIONPAGE
        DiscardPage.objects.create(
            image=qpage_obj.image,
            discard_reason=(
                f"User {user_obj.username} discarded paper "
                f"{qpage_obj.paper.paper_number} page {qpage_obj.page_number} "
                f"question index {qpage_obj.question_index} "
                f"version {qpage_obj.version}"
            ),
        )
        # Set the original question page to have no image, but **DO NOT** delete the question page
        qpage_obj.image = None
        qpage_obj.save()

        # set the associated Markinging task to "OUT_OF_DATE"
        # this also tries to make a new task if possible
        MarkingTaskService().set_paper_marking_task_outdated(
            qpage_obj.paper.paper_number, qpage_obj.question_index
        )

    @transaction.atomic
    def _discard_mobile_page(
        self, user_obj: User, mpage_obj: MobilePage, *, cascade: bool = False
    ) -> None | DiscardPage:
        """Delete a MobilePage object.

        This function **must** do all three things (hence the transaction decorator):
        (1) delete the MobilePage.
        (2) check if the MobilePage was relevant to any MarkingTask objects.
        If it was, out of date those MarkingTask objects.
        (3) Check if the page image in the discarded MobilePage is still
        referenced by other MobilePages. If not, create a DiscardPage referencing it.

        Args:
            user_obj: The user to attribute this action to.
            mpage_obj: The mobile page object to discard.

        Keyword Args:
            cascade: Whether this function should find other MobilePage objects
                referencing the same img, and also delete those.

        Returns:
            The DiscardPage object, if one was created, or None.
        """
        page_img = mpage_obj.image
        if cascade:
            mobile_pages = page_img.mobilepage_set.all().select_related("paper")
        else:
            # turns the MobilePage into a queryset, but +1 query
            mobile_pages = MobilePage.objects.filter(id=mpage_obj.id)
        paper_qidx_dicts = [
            {"paper_number": m.paper.paper_number, "question_index": m.question_index}
            for m in mobile_pages
        ]

        # (1)
        mobile_pages.delete()

        # (2)
        mts = MarkingTaskService()
        for pqdict in paper_qidx_dicts:
            if pqdict["question_index"] == MobilePage.DNM_qidx:
                continue
            mts.set_paper_marking_task_outdated(
                pqdict["paper_number"], pqdict["question_index"]
            )

        # (3)
        # short-circuit `or` saves a db query when `cascade` deletes all mobile pages
        if cascade or page_img.mobilepage_set.count() < 1:
            outdated_tasks = ", ".join(
                [f"{d['paper_number']}-{d['question_index']}" for d in paper_qidx_dicts]
            )
            return DiscardPage.objects.create(
                image=page_img,
                discard_reason=(
                    f"User {user_obj.username} discarded mobile attached "
                    "to marking tasks (paper number, question index): " + outdated_tasks
                ),
            )

        return None

    def discard_pushed_staging_bundle_contents(
        self, user_obj: User, staging_bundle_id: int, *, dry_run: bool = True
    ) -> str:
        """Discard all pages pushed in a given StagingBundle.

        This function operates on pushed bundles, it doesn't do anything to
        StagingBundles or their contents (see
        :method:`ScanService.remove_bundle_by_pk` for deleting StagingBundles).

        Args:
            user_obj: the User who is discarding
            staging_bundle_id: the id of the bundle being discarded

        Keyword Args:
            dry_run: really do it or just pretend?

        Returns:
            A status message about what happened (or, if ``dry_run`` is True,
            what would be attempted).

        Raises:
            ValueError: Attempting to discard the contents of an unpushed bundle.
        """
        staging_bundle_obj = StagingBundle.objects.filter(pk=staging_bundle_id).get()
        if not staging_bundle_obj.pushed:
            raise ValueError(
                f"bundle '{staging_bundle_obj.slug}' hasn't been pushed, please modify it in staging."
            )
        bundle_obj = staging_bundle_obj.bundle_set.get()
        return self._discard_whole_bundle(user_obj, bundle_obj, dry_run=dry_run)

    def _discard_whole_bundle(
        self, user_obj: User, bundle_obj: Bundle, *, dry_run: bool = True
    ) -> str:
        """Discard all pages pushed in a given bundle.

        Args:
            user_obj: the User who is discarding
            bundle_obj: the bundle being discarded

        Keyword Args:
            dry_run: really do it or just pretend?

        Returns:
            A status message about what happened (or, if ``dry_run`` is True,
            what would be attempted).
        """
        msg = ""
        with transaction.atomic():
            for fp in FixedPage.objects.filter(image__bundle=bundle_obj):
                if fp.image:
                    msg += self.discard_pushed_fixed_page(
                        user_obj, fp.pk, dry_run=dry_run
                    )
            for mp in MobilePage.objects.filter(image__bundle=bundle_obj):
                msg += self.discard_pushed_mobile_page(user_obj, mp.pk, dry_run=dry_run)
        return msg

    @transaction.atomic
    def discard_whole_paper_by_number(
        self, user_obj: User, paper_number: int, *, dry_run: bool = True
    ):
        """Discard all pushed pages from the given paper.

        Args:
            user_obj (User): the User who is discarding
            paper_number (int): the paper_number of the paper to be discarded

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
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"A paper with paper_number {paper_number} does not exist"
            ) from e

        msg = ""
        for fp in paper_obj.fixedpage_set.all().select_related("image"):
            # check if that fixedpage has an image
            if fp.image:
                msg += self.discard_pushed_fixed_page(user_obj, fp.pk, dry_run=dry_run)
        # Out of date ID task, even if the paper didn't have an ID page scanned
        if "IDPage" not in msg:
            IdentifyTaskService().set_paper_idtask_outdated(paper_number)

        for mp in paper_obj.mobilepage_set.all():
            msg += self.discard_pushed_mobile_page(user_obj, mp.pk, dry_run=dry_run)
        return msg

    def discard_pushed_fixed_page(
        self, user_obj: User, fixedpage_pk: int, *, dry_run: bool = False
    ) -> str:
        """Discard a fixed page, such an ID page, DNM page or Question page.

        Args:
            user_obj: the User who is discarding
            fixedpage_pk: the id of the fixed page to be discarded

        Keyword Args:
            dry_run: by default, we just do it.  Pass True if you want
                to just pretend.

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

        if fp_obj.page_type == FixedPage.DNMPAGE:
            msg = f"DNMPage paper {fp_obj.paper.paper_number} page {fp_obj.page_number}"
            if dry_run:
                return "DRY-RUN: would drop " + msg
            self._discard_dnm_page(user_obj, fp_obj)
            return "Have dropped " + msg
        elif fp_obj.page_type == FixedPage.IDPAGE:
            msg = f"IDPage paper {fp_obj.paper.paper_number} page {fp_obj.page_number}"
            if dry_run:
                return f"DRY-RUN: would drop {msg}"
            self._discard_id_page(user_obj, fp_obj)
            return (
                f"Have dropped {msg} and "
                "flagged the associated ID-task as 'out of date'"
            )
        elif fp_obj.page_type == FixedPage.QUESTIONPAGE:
            msg = (
                f"QuestionPage for paper {fp_obj.paper.paper_number} "
                f"page {fp_obj.page_number} question index {fp_obj.question_index}"
            )
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
        self, user_obj: User, mobilepage_pk: int, *, dry_run: bool = True
    ) -> str:
        """Discard a mobile page.

        Args:
            user_obj (User): the User who is discarding
            mobilepage_pk (int): the pk of the mobile page to be discarded

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
            mp_obj = MobilePage.objects.get(pk=mobilepage_pk)
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"A mobile page with pk {mobilepage_pk} does not exist"
            ) from e

        msg = (
            f"a MobilePage for paper {mp_obj.paper.paper_number} "
            f"question index {mp_obj.question_index}"
        )
        if dry_run:
            return f"DRY-RUN: would drop {msg}"
        self._discard_mobile_page(user_obj, mp_obj)
        return (
            f"Have dropped {msg} and "
            "flagged the associated marking task as 'out of date'"
        )

    def discard_pushed_image_from_pk(self, user_obj: User, image_pk: int) -> None:
        """Discard all pushed pages referencing the keyed Image.

        Args:
            user_obj: the user to attribute this action to.
            image_pk: the id of the image to discard and cascade.
        """
        try:
            image_obj = Image.objects.get(pk=image_pk)
        except ObjectDoesNotExist as e:
            raise ValueError(f"An image with pk {image_pk} does not exist.") from e
        # Assume FixedPage, MobilePage, or DiscardPage
        if image_obj.fixedpage_set.exists():
            self.discard_pushed_fixed_page(
                user_obj, image_obj.fixedpage_set.first().pk, dry_run=False
            )
        elif image_obj.mobilepage_set.exists():
            self._discard_mobile_page(
                user_obj, image_obj.mobilepage_set.first(), cascade=True
            )
        else:
            pass

    def discard_pushed_page_cmd(
        self,
        username: str,
        *,
        fixedpage_pk: int | None = None,
        mobilepage_pk: int | None = None,
        dry_run: bool = True,
    ) -> str:
        """Given the pk of either a fixed-page or a mobile-page discard it.

        This is a simple wrapper for various 'discard' functions.

        Args:
            username: the name of the user doing the discarding. Note - must be a manager.

        Keyword Args:
            fixedpage_pk: the pk of the fixed page to discard
            mobilepage_pk: the pk of the mobile page to discard
            dry_run: when true, simulate the discard without doing it, else actually do the discard.
        """
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

    @staticmethod
    def _assign_discard_to_fixed_page(
        user_obj: User, discard_obj: DiscardPage, paper_number: int, page_number: int
    ) -> None:
        # we don't need the Paper, but on failure we get a more specific error
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except ObjectDoesNotExist as e:
            raise ValueError(f"Cannot find a paper with number = {paper_number}") from e

        with transaction.atomic():
            fixed_pages = FixedPage.objects.filter(
                paper=paper_obj, page_number=page_number
            )
            if not fixed_pages:
                raise ValueError(
                    f"Paper {paper_number} does not have fixed pages with page number {page_number}"
                )
            for fpage_obj in fixed_pages:
                if fpage_obj.image:
                    # TODO: annoying corner case if 1 hasn't but 2 has?
                    raise ValueError(
                        f"Fixed page {page_number} of paper {paper_number} already has an image."
                    )
                # assign the image to the fixed page
                fpage_obj.image = discard_obj.image
                fpage_obj.save()
                if fpage_obj.page_type == FixedPage.DNMPAGE:
                    pass
                elif fpage_obj.page_type == FixedPage.IDPAGE:
                    IdentifyTaskService().set_paper_idtask_outdated(paper_number)
                elif fpage_obj.page_type == FixedPage.QUESTIONPAGE:
                    MarkingTaskService().set_paper_marking_task_outdated(
                        paper_number, fpage_obj.question_index
                    )
                else:
                    raise RuntimeError(
                        "Tertium non datur: all FixedPage must be DNM, ID, or QuestionPage"
                        f" pk = {fpage_obj.pk} in paper {paper_number} page {page_number}."
                    )
            # finally (and still inside the atomic) delete the discard page
            discard_obj.delete()

    @transaction.atomic
    def _assign_discard_page_to_mobile_page(
        self,
        discard_pk: int,
        paper_number: int,
        assign_to_question_indices: list[int],
    ) -> None:
        """Low-level routine to assign a discard image by attaching it to one or more questions in an ad hoc way.

        Generally, this will be a page without QR codes such as a self-scanned
        "homework" page or an "oops that wasn't scrap" or a sheet of plain paper.

        Args:
            user_obj: which user, as a database object.
            discard_pk: which discarded page.
            paper_number: which paper to assign it o.
            assign_to_question_indices: which questions, by a list of
                one-based indices, should we assign this discarded page to.
        """
        try:
            discard_obj = DiscardPage.objects.get(pk=discard_pk)
        except ObjectDoesNotExist as e:
            raise ValueError(f"Cannot find discard page with pk = {discard_pk}") from e

        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except ObjectDoesNotExist as e:
            raise ValueError(f"Cannot find a paper with number = {paper_number}") from e

        for qi in assign_to_question_indices:
            # TODO: what if there are no question pages?  Maybe this should query the version map instead?
            # get the version from an associated question-page
            # (first() is used instead of get() b/c multiple QuestionPages can share a physical
            # page; in Plom's tooling they would have a common version, although that restriction
            # should be relaxed in the future, hence the TODO above about using qvmap here.)
            version = (
                FixedPage.objects.filter(
                    paper=paper_obj, question_index=qi, page_type=FixedPage.QUESTIONPAGE
                )
                .first()
                .version
            )
            MobilePage.objects.create(
                paper=paper_obj,
                question_index=qi,
                image=discard_obj.image,
                version=version,
            )
        # otherwise, if question index list empty, make a non-marked MobilePage
        if not assign_to_question_indices:
            MobilePage.objects.create(
                paper=paper_obj,
                image=discard_obj.image,
                question_index=MobilePage.DNM_qidx,
                version=0,
            )

        # delete the discard page
        discard_obj.delete()
        # reset the associated marking tasks
        for qi in assign_to_question_indices:
            MarkingTaskService().set_paper_marking_task_outdated(paper_number, qi)

    @classmethod
    def assign_discard_page_to_fixed_page(
        cls, user_obj: User, discard_pk: int, paper_number: int, page_number: int
    ) -> None:
        """Reassign the given discard page to a fixed page at the given paper/page.

        If there is more than one QuestionPage attached to that page,
        the image from the discard will be assigned to all of them.

        The discard page will be deleted.

        Args:
            user_obj: A django User who is doing the reassignment of the discard page.
            discard_pk: the pk of the discard page.
            paper_number: the number of the paper to which the discard is being reassigned.
            page_number: the number of the page in the given paper to which the discard is reassigned.
        """
        try:
            discard_obj = DiscardPage.objects.get(pk=discard_pk)
        except ObjectDoesNotExist as e:
            raise ValueError(f"Cannot find discard page with id {discard_pk}") from e

        cls._assign_discard_to_fixed_page(
            user_obj, discard_obj, paper_number, page_number
        )

    def reassign_discard_page_to_fixed_page_cmd(
        self, username: str, discard_pk: int, paper_number: int, page_number: int
    ) -> None:
        """A wrapper around the assign_discard_page_to_fixed_page command.

        Args:
            username: the name of the user who is doing the reassignment.
                Must be a manager.
            discard_pk: the pk of the discard page to be reassigned.
            paper_number: the number of the paper containing the fixed page.
            page_number: the page number of the fixed page.
        """
        try:
            user_obj = User.objects.get(
                username__iexact=username, groups__name="manager"
            )
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions."
            ) from e
        try:
            discard_obj = DiscardPage.objects.get(pk=discard_pk)
        except ObjectDoesNotExist as e:
            raise ValueError(f"Cannot find discard page with id {discard_pk}") from e

        self._assign_discard_to_fixed_page(
            user_obj, discard_obj, paper_number, page_number
        )

    def reassign_discard_page_to_mobile_page_cmd(
        self,
        username: str,
        discard_pk: int,
        paper_number: int,
        assign_to_question_indices: list[int],
    ) -> None:
        """Reassign a discard image by attaching it to one or more questions in an ad hoc way.

        Generally, this will be a page without QR codes such as a self-scanned
        "homework" page or an "oops that wasn't scrap" or a sheet of plain paper.

        Args:
            username: the name of the user who is doing the reassignment.
                Must be a manager.
            discard_pk: the pk of the discard page to be reassigned.
            paper_number: the number of the paper containing the fixed page.
            assign_to_question_indices: a list of the questions on the
                discard page. A mobile page is created for each.
                An empty list creates a DNM mobile page.
        """
        try:
            _ = User.objects.get(username__iexact=username, groups__name="manager")
        except ObjectDoesNotExist as e:
            raise ValueError(
                f"User '{username}' does not exist or has wrong permissions."
            ) from e

        self._assign_discard_page_to_mobile_page(
            discard_pk, paper_number, assign_to_question_indices
        )

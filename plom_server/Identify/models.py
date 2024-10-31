# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone

from Base.models import HueyTaskTracker
from Papers.models import Paper


class PaperIDTask(models.Model):
    """Represents a test-paper that needs to be identified.

    paper: reference to Paper that needs to be IDed.
    latest_action: reference to `PaperIDAction`, the latest identification
        for the paper.  "Latest" need not refer to time, it can be
        moved around to different `PaperIDAction`s if you wish.
    priority: a float priority that provides the ordering for tasks
        presented for IDing, zero by default.
    assigned_user: reference to User, the user currently attached to
        the task.  Can be null, can change over time. Notice that when
        a tasks has status "out" or "complete" then it must have an
        assigned_user, and when it is set to "to do" or "out of date"
        it must have assigned_user set to none.
    time: the time the task was originally created.
        TODO: is this used for anything?
    last_update: the time of the last update to the task (updated whenever model is saved)
    status: str, represents the status of the task: not started, sent
        to a client, completed, out of date.

    PaperIDTasks have a ``status``, represented by a choice kwarg, see
    https://docs.djangoproject.com/en/4.2/ref/models/fields/#choices
    for more info.
    There is *currently* some complexity about updating
    this b/c there are changes that MUST be made (but are not automatically
    made) in the Actions which are attached to this Task.

    Note: Another table, :class:`MarkingTask`, shares similar status
    choices and some other fields; once upon a time they shared a common
    subclass.
    """

    paper = models.ForeignKey(Paper, on_delete=models.CASCADE)
    latest_action = models.OneToOneField(
        "PaperIDAction", unique=True, null=True, on_delete=models.SET_NULL
    )
    iding_priority = models.FloatField(null=True, default=0.0)

    StatusChoices = models.IntegerChoices("Status", "TO_DO OUT COMPLETE OUT_OF_DATE")
    TO_DO = StatusChoices.TO_DO
    OUT = StatusChoices.OUT
    COMPLETE = StatusChoices.COMPLETE
    OUT_OF_DATE = StatusChoices.OUT_OF_DATE

    assigned_user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time = models.DateTimeField(default=timezone.now)
    status = models.IntegerField(
        null=False, choices=StatusChoices.choices, default=TO_DO
    )
    last_update = models.DateTimeField(auto_now=True)


class PaperIDAction(models.Model):
    """Represents an identification of a test-paper.

    user: reference to User, the user who performed the action
    time: datetime, the time the action took place
    task: reference to PaperIDTask, the task connected to the action.

    is_valid: this Action is valid or not.  There is some... complexity
        about this.  There can be multiple Actions attached to a single
        Task.  In theory only one of them (at most one of them) can be
        valid.  Currently this IS NOT ENFORCED, so callers MUST maintain
        this logic themselves.
        There are states that are possible but we don't want to get into
        them: for example (but not exhaustive), you should not have an
        ``status=OutOfDate`` with a valid IDAction attached to that Task.
    student_name:
    student_id:

    Because of the OneToOneField in PaperIDTask, there will also be an
    autogenerated field called ``paperidtask`` (note lowercase).
    """

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    time = models.DateTimeField(default=timezone.now)
    task = models.ForeignKey(PaperIDTask, null=True, on_delete=models.SET_NULL)

    is_valid = models.BooleanField(default=True)
    student_name = models.TextField(null=True, default="", unique=False)
    student_id = models.TextField(null=True, default="", unique=False)
    # Do not set ID field uniqueness here, since this does not take
    # into account the fact that we can ignore student-ids in
    # OUT_OF_DATE tasks. But then we must enforce the uniqueness in
    # our identify_paper code 'by hand' and take into account blank
    # IDs (as per #2827) - they can be non-unique.


class IDPrediction(models.Model):
    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    student_id = models.CharField(null=True, max_length=255)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    predictor = models.CharField(null=False, max_length=255)
    certainty = models.FloatField(null=False, default=0.0)


class IDReadingHueyTaskTracker(HueyTaskTracker):
    """Support running the ID-box extraction and ID prediction in the background.

    Note that this inherits fields from the base class table.  Note that
    this has no additional fields.
    """

    @classmethod
    def set_message_to_user(cls, pk, message: str):
        """Set the user-readible message string."""
        with transaction.atomic(durable=True):
            cls.objects.select_for_update().filter(pk=pk).update(message=message)

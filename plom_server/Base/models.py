# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from huey.signals import SIGNAL_ERROR, SIGNAL_INTERRUPTED

from django.db import models
from django.db import transaction
from django.contrib.auth.models import User
from django_huey import get_queue
from django.utils import timezone
from polymorphic.models import PolymorphicModel

import logging

# TODO: what is this?  It is happening at import-time... scary
# It comes from Django-Huey project and allows you to have multiple
# task queues
# TODO: this is used for the decorators to define the signal handlers
# below, so it must presumably somehow be lazy...  but this :-(
queue = get_queue("tasks")


class HueyTaskTracker(models.Model):
    """A general-purpose model for tracking Huey tasks.

    It keeps track of a Huey task's ID, the time created, and the
    status. Also, this is where we define the functions for handling
    signals sent from the huey consumer.

    TODO: well we don't actually define those here, they are in global
    scope outside this class.  See TODO above.

    When you create one of these, set status to ``TO_DO`` or ``STARTING``,
    choosing ``STARTING`` if just about to enqueue a Huey task.
    The Huey task should (eventually) update the status to ``RUNNING``.
    In the meantime, you can change status to ``QUEUED`` (provided you
    are careful not to overwrite ``RUNNING``!)
    Generally the Huey task itself should set status ``COMPLETE``.

    The difference between STARTING, QUEUED, and RUNNING is rather
    sensitive to timing.  Caller can set STARTING and try to set
    QUEUED (but must defer to the Huey task itself about RUNNING.

    .. caution:: These statuses are not just symbolic constants; they
        also appear as strings through the code as
        "To Do", "Starting", "Queued", "Running", "Error", "Complete".
        Note the difference in cases.  They are displayed to users.
        They are also used in logic tests.

    ``obsolete=True`` is a "light deletion; no one cares for the result
    and it should not be used.  It is ok to change status (e.g., a
    background task finishes a chore that no one cares about anymore is
    free to complete the chore---or not!)  Obsolete is not the same as
    ``ERROR``: a task could be in an error state but still relevant, for
    example, being displayed in a UI to show users it has errored.
    """

    StatusChoices = models.IntegerChoices(
        "status", "TO_DO STARTING QUEUED RUNNING COMPLETE ERROR"
    )
    TO_DO = StatusChoices.TO_DO
    STARTING = StatusChoices.STARTING
    QUEUED = StatusChoices.QUEUED
    RUNNING = StatusChoices.RUNNING
    COMPLETE = StatusChoices.COMPLETE
    ERROR = StatusChoices.ERROR

    huey_id = models.UUIDField(null=True)
    status = models.IntegerField(
        null=False, choices=StatusChoices.choices, default=TO_DO
    )
    created = models.DateTimeField(default=timezone.now, blank=True)
    message = models.TextField(default="")
    last_update = models.DateTimeField(auto_now=True)
    obsolete = models.BooleanField(default=False)

    def transition_back_to_todo(self):
        # TODO: which states are allowed to transition here?
        self.huey_id = None
        self.status = self.TO_DO
        self.save()

    def reset_to_do(self):
        # subclasses might subclass to do more
        self.transition_back_to_todo()

    def _transition_to_starting(self):
        assert self.status == self.TO_DO, (
            f"Tracker cannot transition from {self.get_status_display()}"
            " to Starting (only from To_Do state)"
        )
        assert self.huey_id is None, (
            "Tracker must have id None to transition to Starting"
            f" but we have id={self.huey_id}"
        )
        self.status = self.STARTING
        self.save()

    @classmethod
    def transition_to_running(cls, pk, huey_id):
        """Move to the Running state in a safe way using locking.

        We don't care if the tracker is obsolete or not; that is the
        callers concern.
        """
        with transaction.atomic(durable=True):
            # Get a lock with select_for_update; this is important b/c this code
            # is used in a race with Queued.
            tr = cls.objects.select_for_update().get(pk=pk)
            assert tr.status in (cls.STARTING, cls.QUEUED), (
                f"Tracker cannot transition from {tr.get_status_display()}"
                " to Running (only from Starting or Queued)"
            )
            # Note: could use an inline update if we didn't have the assert
            tr.huey_id = huey_id
            tr.status = cls.RUNNING
            tr.save()

    @classmethod
    def transition_to_queued_or_running(cls, pk, huey_id):
        """Move to the Queued state using locking, or a no-op if we're already Running.

        We don't care if the tracker is obsolete or not; that is the
        callers concern.
        """
        with transaction.atomic(durable=True):
            # We are racing with Huey: it will try to update to RUNNING,
            # we try to update to QUEUED, but only if Huey doesn't get
            # there first.  If Huey updated already, we want a no-op.
            cls.objects.select_for_update().filter(pk=pk, status=cls.STARTING).update(
                huey_id=huey_id, status=cls.QUEUED
            )

            # # a slightly stricter implementation:
            # tr = cls.objects.select_for_update().get(pk=pk)
            # if tr.status == cls.RUNNING:
            #     assert tr.huey_id == huey_id, (
            #         f"We were already in the RUNNING state with huey id {tr.huey_id} "
            #         f"when you tried to enqueue with a different huey id {huey_id}"
            #     )
            #     return
            # assert tr.status == cls.STARTING, (
            #     f"Tracker cannot transition from {tr.get_status_display()}"
            #     " to Queued (only from Starting)"
            # )
            # tr.huey_id = huey_id
            # tr.status = cls.QUEUED
            # tr.save()

    @classmethod
    def transition_to_complete(cls, pk):
        """Move to the complete state.

        We don't care if the tracker is obsolete or not; that is the
        callers concern.
        """
        # TODO: should we interact with other non-Obsolete chores?
        # Currently we prevent multiple non-Obsolete Chores at creation
        with transaction.atomic(durable=True):
            tr = cls.objects.select_for_update().get(pk=pk)
            assert tr.status == cls.RUNNING, (
                f"Tracker cannot transition from {tr.get_status_display()}"
                " to Complete (only from Running)"
            )
            tr.huey_id = None
            tr.status = cls.COMPLETE
            tr.save()

    def set_as_obsolete(self):
        """Move to the obsolete state and save, a sort of "light deletion"."""
        self.obsolete = True
        self.save()

    def set_as_obsolete_with_error(self, errmsg: str) -> None:
        """Move to the error state and set obsolete."""
        self.huey_id = None
        self.status = self.ERROR
        self.message = errmsg
        self.obsolete = True
        self.save()

    def transition_to_error(self, errmsg: str) -> None:
        """Move to the error state."""
        self.huey_id = None
        self.status = self.ERROR
        self.message = errmsg
        self.save()


# ---------------------------------
# Define a singleton model as per
# https://steelkiwi.com/blog/practical-application-singleton-design-pattern/
#
# Then use this to define tables for PrenamingSetting and ClasslistCSV
# ---------------------------------


class SingletonBaseModel(models.Model):
    """We define a singleton model for the test-specification.

    This abstract model ensures that any derived models have at most a
    single row.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class BaseTask(PolymorphicModel):
    """A base class for all "tasks" that are sent from the server to the PyQT client.

    Status is represented by a choice kwarg, see
    https://docs.djangoproject.com/en/4.2/ref/models/fields/#choices
    for more info

    assigned_user: reference to User, the user currently attached to
        the task.  Can be null, can change over time. Notice that when
        a tasks has status "out" or "complete" then it must have an
        assigned_user, and when it is set to "to do" or "out of date"
        it must have assigned_user set to none.
    time: the time the task was originally created.
        TODO: is this used for anything?
    last_update: the time of the last update to the task (updated whenever model is saved)
    status: str, represents the status of the task: not started, sent to a client, completed, out of date.

    """

    # TODO: UUID for indexing

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


class BaseAction(PolymorphicModel):
    """A base class for all "actions" that pertain to marker user management.

    I.E., grading a question, assigning a task, assigning the task to a new user, etc
    with the goal of saving a "history" of all marking/user management actions.

    user: reference to User, the user who performed the action
    time: datetime, the time the action took place
    task: reference to BaseTask, the task connected to the action
    """

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    time = models.DateTimeField(default=timezone.now)
    task = models.ForeignKey(BaseTask, null=True, on_delete=models.SET_NULL)


class Tag(models.Model):
    """Represents a text entry that can have a many-to-one relationship with another table.

    This is an abstract class that should be extended in other apps.

    user: reference to a User instance, the user who created the task
    time: when the tag was first created
    text: the text contents of the tag
    """

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time = models.DateField(default=timezone.now)
    text = models.TextField(null=False)

    class Meta:
        abstract = True

    def __str__(self):
        """Return the tag's text."""
        return str(self.text)


# ---------------------------------
# Define the signal handlers for huey tasks.
# ---------------------------------

# TODO: I am concerned that these receive signals from unrelated Huey tasks
# on the same computer, such as our test suite Issue #2800.


@queue.signal(SIGNAL_ERROR)
def on_huey_task_error(signal, task, exc):
    """Action to take when a Huey task fails."""
    logging.warn(f"Error in task {task.id} {task.name} {task.args} - {exc}")
    print(f"Error in task {task.id} {task.name} {task.args} - {exc}")

    # Note: using filter except of a exception on DoesNotExist because I think
    # the exception handling was rewinding some atomic transactions
    if not HueyTaskTracker.objects.filter(huey_id=task.id).exists():
        # task has been deleted from underneath us, or did not exist yet b/c of race conditions
        print(
            f"(Error) Task {task.id} {task.name} with args {task.args}"
            " is no longer (or not yet) in the database."
        )
        return

    with transaction.atomic():
        task_obj = HueyTaskTracker.objects.get(huey_id=task.id)
        task_obj.status = HueyTaskTracker.ERROR
        task_obj.message = exc
        task_obj.save()


@queue.signal(SIGNAL_INTERRUPTED)
def on_huey_task_interrupted(signal, task):
    print(f"Interrupt was sent to task {task.id} - {task.name} {task.args}")

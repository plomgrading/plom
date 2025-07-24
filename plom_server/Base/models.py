# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

import logging

import huey
import huey.api
import huey.signals
from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils import timezone
from django_huey import get_queue


# TODO: Using the @signal decorator did not work with both queues
# from django_huey import signal
main_queue = get_queue("chores")
parent_queue = get_queue("parentchores")


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
    def bulk_transition_to_queued_or_running(cls, pk_huey_id_pair_list):
        """Move to the Queued state using locking, or a no-op if we're already Running.

        A bulk version of method 'transition_to_queued_or_running'. Note that it
        is set as a durable-transaction, so that it must be the outermost atomic
        transaction and ensures that any database changes are committed when it
        runs without errors. See django documentation for more details.
        """
        with transaction.atomic(durable=True):
            for pk, huey_id in pk_huey_id_pair_list:
                cls.objects.select_for_update().filter(
                    pk=pk, status=cls.STARTING
                ).update(huey_id=huey_id, status=cls.QUEUED)

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

    @classmethod
    def set_every_task_obsolete(cls):
        """Set every single task as obsolete."""
        cls.objects.all().update(obsolete=True)

    def transition_to_error(self, errmsg: str) -> None:
        """Move ourself to the error state."""
        self.huey_id = None
        self.status = self.ERROR
        self.message = errmsg
        self.save()

    @classmethod
    def transition_chore_to_error(cls, pk: int, errmsg: str) -> None:
        """Move a chore to the error state via its primary key."""
        with transaction.atomic(durable=True):
            tr = cls.objects.select_for_update().get(pk=pk)
            tr.transition_to_error(errmsg)

    @classmethod
    def set_every_task_with_status_error_obsolete(cls):
        """Set every single task with status=error as obsolete."""
        with transaction.atomic():
            cls.objects.filter(status=cls.ERROR).update(obsolete=True)


# ---------------------------------
# Define a singleton model as per
# https://steelkiwi.com/blog/practical-application-singleton-design-pattern/
# ---------------------------------


class SingletonABCModel(models.Model):
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
        raise NotImplementedError("load() should be overridden in derived classes")


class Tag(models.Model):
    """Represents a text entry that can have a many-to-one relationship with another table.

    This is an abstract class that should be extended in other apps.

    user: reference to a User instance, the user who created the tag
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


class NewSettingsModel(models.Model):
    key = models.CharField(max_length=64, unique=True)
    value = models.JSONField(default=str)

    def __str__(self):
        """Convert a key-value setting to a string representation."""
        return f"Key-Value setting id {self.id}: {self.key} = {self.value}"


class NewSettingsBooleanModel(models.Model):
    key = models.CharField(max_length=64, unique=True)
    value = models.BooleanField()


class SettingsModel(SingletonABCModel):
    """Global configurable settings."""

    # TODO: intention is a tri-state: "permissive", "per-user", "locked"
    who_can_create_rubrics = models.TextField(default="permissive")
    who_can_modify_rubrics = models.TextField(default="per-user")

    @classmethod
    def load(cls):
        """Return the singleton instance of the SettingsModel."""
        obj, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                "who_can_create_rubrics": "permissive",
                "who_can_modify_rubrics": "per-user",
            },
        )
        return obj


class BaseImage(models.Model):
    """Table to store an image (usually a scanned page image).

    image_file (ImageField): the django-imagefield storing the image for the server.
        In the future this could be a url to some cloud storage. Note that this also
        tells django where to automagically compute+store height/width information on save

    image_hash (str): the sha256 hash of the image

    height (int): the height of the image in px (auto-populated on
        save by django). Note that this height is the *raw* height in
        pixels before any exif rotations and any plom rotations.

    width (int): the width of the image in px (auto-populated on
        save by django).  Note that this width is the *raw* width in
        pixels before any exif rotations and any plom rotations.
    """

    def _image_save_path(self, filename: str) -> str:
        """Create a path to which the associated base image file should be saved.

        Args:
            filename: the name of the file to be saved at the created path.

        Returns:
            The string of the path to which the image file will be saved
            (relative to the media directory, and including the actual filename).
        """
        return f"page_images/{filename}"

    image_file = models.ImageField(
        null=False,
        upload_to=_image_save_path,
        # tell Django where to automagically store height/width info on save
        height_field="height",
        width_field="width",
    )
    image_hash = models.CharField(null=True, max_length=64)
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)


# ---------------------------------
# Define the signal handlers for huey tasks.
# ---------------------------------

# TODO: I am concerned that these receive signals from unrelated Huey tasks
# on the same computer, such as our test suite Issue #2800.


# @signal(huey.signals.SIGNAL_ERROR)
@main_queue.signal(huey.signals.SIGNAL_ERROR)
def on_huey_task_error(signal, task: huey.api.Task, exc):
    """Action to take when a Huey task fails."""
    logging.warn(f"Error in task {task.id} {task.name} {task.args} - {exc}")
    print(f"Error in task {task.id} {task.name} {task.args} - {exc}")

    # Note: using filter except of a exception on DoesNotExist because I think
    # the exception handling was rewinding some atomic transactions
    if not HueyTaskTracker.objects.filter(huey_id=task.id).exists():
        # task has been deleted from underneath us, or did not exist yet b/c of race conditions
        # or perhaps this huey task is not being tracked by a one of our trackers
        # (for example, it may have a parent task that is doing the tracking)
        print(
            f"(Error) Task {task.id} {task.name} with args {task.args}"
            " is no longer (or not yet or never will be) in the database."
        )
        return

    with transaction.atomic():
        task_obj = HueyTaskTracker.objects.get(huey_id=task.id)
        task_obj.status = HueyTaskTracker.ERROR
        task_obj.message = exc
        task_obj.save()


# @signal(huey.signals.SIGNAL_INTERRUPTED)
@main_queue.signal(huey.signals.SIGNAL_INTERRUPTED)
def on_huey_task_interrupted(signal, task: huey.api.Task):
    print(f"Interrupt was sent to task {task.id} - {task.name} {task.args}")


@parent_queue.signal(huey.signals.SIGNAL_ERROR)
def on_huey_parent_task_error(signal, task: huey.api.Task, exc):
    """Action to take when a Huey task fails.

    This is slightly different from the regular one above b/c all parent tasks
    should always have a tracker (but child tasks might not).
    """
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


@parent_queue.signal(huey.signals.SIGNAL_INTERRUPTED)
def on_huey_parent_task_interrupted(signal, task: huey.api.Task):
    # TODO: this code is duplicated b/c @signal decorate did work for both queues
    print(f"Interrupt was sent to task {task.id} - {task.name} {task.args}")

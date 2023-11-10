# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from huey.signals import (
    SIGNAL_EXECUTING,
    SIGNAL_ERROR,
    SIGNAL_COMPLETE,
    SIGNAL_INTERRUPTED,
)

from django.db import models
from django.contrib.auth.models import User
from django_huey import get_queue
from django.utils import timezone
from polymorphic.models import PolymorphicModel

import logging

# TODO: what is this?  It is happening at import-time... scary
# It comes from Django-Huey project and allows you to have multiple
# task queues
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
    TODO: ``ERROR`` is still in-flux.

    The difference between STARTING, QUEUED, and RUNNING is rather
    sensitive to timing.  Caller can set STARTING and try to set
    QUEUED (but must defer to the Huey task itself about RUNNING.
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
        return self.text


# ---------------------------------
# Define the signal handlers for huey tasks.
# if the task has the kwarg "quiet=True" then
# we ignore the signals
# otherwise we use the signals to update information
# in the database.
# ---------------------------------

# TODO: I am concerned that these receive signals from unrelated Huey tasks
# on the same computer, such as our test suite Issue #2800.


@queue.signal(SIGNAL_EXECUTING)
def start_task(signal, task):
    if task.kwargs.get("quiet", False):
        return

    # TODO: this lookup of HueyTraskTrackers by ID has races because
    # the task can easily start before we have a change to save this ID.

    # Note: using filter except of a exception on DNE because I think
    # the exception handling was rewinding some atomic transations
    if not HueyTaskTracker.objects.filter(huey_id=task.id).exists():
        # task has been deleted from underneath us, or did not exist yet b/c of race conditions
        print(
            f"(Started) Task {task.id} {task.name} with args {task.args}"
            " is no longer (or not yet) in the database."
        )
        return

    task_obj = HueyTaskTracker.objects.get(huey_id=task.id)
    task_obj.status = HueyTaskTracker.STARTED
    task_obj.save()


@queue.signal(SIGNAL_COMPLETE)
def end_task(signal, task):
    if task.kwargs.get("quiet", False):
        return
    try:
        task_obj = HueyTaskTracker.objects.get(huey_id=task.id)
        task_obj.status = HueyTaskTracker.COMPLETE
        task_obj.save()
    except HueyTaskTracker.DoesNotExist:
        # task has been deleted from underneath us, or did not exist yet b/c of race conditions
        print(
            f"(Completed) Task {task.id} {task.name} with args {task.args}"
            " is no longer (or not yet) in the database."
        )


@queue.signal(SIGNAL_ERROR)
def error_task(signal, task, exc):
    logging.warn(f"Error in task {task.id} {task.name} {task.args} - {exc}")
    print(f"Error in task {task.id} {task.name} {task.args} - {exc}")
    if task.kwargs.get("quiet", False):
        return
    try:
        task_obj = HueyTaskTracker.objects.get(huey_id=task.id)
        task_obj.status = HueyTaskTracker.ERROR
        task_obj.message = exc
        task_obj.save()
    except HueyTaskTracker.DoesNotExist:
        # task has been deleted from underneath us, or did not exist yet b/c of race conditions
        print(
            f"(Error) Task {task.id} {task.name} with args {task.args}"
            " is no longer (or not yet) in the database."
        )


@queue.signal(SIGNAL_INTERRUPTED)
def interrupt_task(signal, task):
    print(f"Interrupt sent to task {task.id} - {task.name} {task.args}")

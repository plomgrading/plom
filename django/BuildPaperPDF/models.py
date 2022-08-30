from datetime import datetime
from huey.signals import SIGNAL_EXECUTING, SIGNAL_ERROR, SIGNAL_COMPLETE

from django.db import models
from django_huey import get_queue
from polymorphic.models import PolymorphicModel

queue = get_queue('tasks')


class HueyTask(PolymorphicModel):
    huey_id = models.UUIDField(null=True)
    status = models.CharField(max_length=20)
    created = models.DateTimeField(default=datetime.now, blank=True)
    message = models.TextField(default="")

    @classmethod
    @queue.signal(SIGNAL_EXECUTING)
    def start_task(signal, task):
        task_obj = HueyTask.objects.get(huey_id=task.id)
        task_obj.status = 'started'
        task_obj.save()

    @classmethod
    @queue.signal(SIGNAL_COMPLETE)
    def end_task(signal, task):
        task_obj = HueyTask.objects.get(huey_id=task.id)
        task_obj.status = 'complete'
        task_obj.save()

    @classmethod
    @queue.signal(SIGNAL_ERROR)
    def error_task(signal, task, exc):
        task_obj = HueyTask.objects.get(huey_id=task.id)
        task_obj.status = 'error'
        task_obj.message = exc
        task_obj.save()


class PDFTask(HueyTask):
    paper_number = models.IntegerField()
    pdf_file_path = models.TextField(default="")

    def __str__(self):
        return "Task Object " + str(self.paper_number)

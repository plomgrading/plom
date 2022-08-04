from django.db import models


class ClasslistCSV(models.Model):
    # TODO - set a better upload path
    csv_file = models.FileField(upload_to=".")
    valid = models.BooleanField(default=False, null=False)
    warnings_errors_list = models.JSONField()


class Student(models.Model):
    """Table to store information about students who have taken this
    assessment. Note, name is stored as a single field.

    student_id (str): The students id-number or id-string. Must be unique.
    student_name (str): The name of the student (as a single text field)
    paper_number (int): The paper_number assigned to this
        student. TODO = this will be a foreign key field to the paper
        table.

    """

    # To understand why a single name-field, see
    # https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/

    student_id = models.TextField(null=True, unique=True)
    student_name = models.TextField(null=False)
    paper_number = models.PositiveIntegerField(null=True)

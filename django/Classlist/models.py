from django.db import models


class Student(models.Model):
    """Table to store information about students who have taken this
    assessment. Note, name is stored as a single field.

    student_id (str): The students id-number or id-string. Must be unique.
    student_name (str): The name of the student (as a single text field)

    """

    # To understand why a single name-field, see
    # https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/

    student_id = models.TextField(null=True, unique=True)
    student_name = models.TextField(null=False)

from django.core.files import File
from django.db import transaction

from Preparation.models import PrenameClasslistCSV, PrenameStudent

import csv
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

log = logging.getLogger("ClasslistService")


class PrenameClasslistCSVService:
    def take_classlist_from_upload(self, in_memory_file):
        from plom.create.classlistValidator import PlomClasslistValidator

        # delete any old classlists
        self.delete_classlist_csv()
        # now save the in-memory file to a tempfile and validate
        tmp_csv = Path(NamedTemporaryFile(delete=False).name)
        with open(tmp_csv, "wb") as fh:
            for chunk in in_memory_file:
                fh.write(chunk)

        vlad = PlomClasslistValidator()
        success, werr = vlad.validate_csv(tmp_csv)

        tmp_csv.unlink()

        with transaction.atomic():
            dj_file = File(in_memory_file, name="classlist.csv")
            cl_obj = PrenameClasslistCSV(
                valid=success, csv_file=dj_file, warnings_errors_list=werr
            )
            cl_obj.save()

        return (success, werr)

    @transaction.atomic()
    def is_there_a_classlist(self):
        return PrenameClasslistCSV.objects.exists()
    
    @transaction.atomic()
    def get_classlist_csv_filepath(self):
        return PrenameClasslistCSV.objects.get().csv_file.path

    @transaction.atomic()
    def delete_classlist_csv(self):
        # explicitly delete the file, since it is not done automagically by django
        # TODO - make this a bit cleaner.
        if PrenameClasslistCSV.objects.exists():
            Path(PrenameClasslistCSV.objects.get() .csv_file.path).unlink()
            PrenameClasslistCSV.objects.filter().delete()


class PrenameStudentService:
    @transaction.atomic
    def how_many_students(self):
        return PrenameStudent.objects.all().count()

    @transaction.atomic
    def are_there_students(self):
        return PrenameStudent.objects.exists()
    
    @transaction.atomic()
    def get_students(self):
        return list(
            PrenameStudent.objects.all().values(
                "student_id", "student_name", "paper_number"
            )
        )

    @transaction.atomic()
    def add_student(self, student_id, student_name, paper_number=None):
        # will raise an integrity error if id not unique

        s_obj = PrenameStudent(student_id=student_id, student_name=student_name)
        # set the paper_number if present
        if paper_number:
            s_obj.paper_number = paper_number
        s_obj.save()

    @transaction.atomic()
    def remove_all_students(self):
        PrenameStudent.objects.all().delete()

    @transaction.atomic()
    def use_classlist_csv(self):
        cl_obj = PrenameClasslistCSV.objects.get()
        classlist_csv = cl_obj.csv_file.path
        with open(classlist_csv) as fh:
            csv_reader = csv.DictReader(fh, skipinitialspace=True)
            # make sure headers are lowercase
            old_headers = csv_reader.fieldnames
            # since this has been validated we know it has 'id', 'name', 'paper_number'
            csv_reader.fieldnames = [x.lower() for x in old_headers]
            # now we have lower case field names
            for row in csv_reader:
                self.add_student(row["id"], row["name"], row["paper_number"])

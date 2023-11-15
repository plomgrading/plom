# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Natalie Balashov

import csv
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.db import transaction

from ..models import StagingClasslistCSV, StagingStudent
from ..services import PrenameSettingService


log = logging.getLogger("ClasslistService")


class StagingClasslistCSVService:
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
            cl_obj = StagingClasslistCSV(
                valid=success, csv_file=dj_file, warnings_errors_list=werr
            )
            cl_obj.save()

        return (success, werr)

    @transaction.atomic()
    def is_there_a_classlist(self):
        return StagingClasslistCSV.objects.exists()

    @transaction.atomic()
    def get_classlist_csv_filepath(self):
        return StagingClasslistCSV.objects.get().csv_file.path

    @transaction.atomic()
    def delete_classlist_csv(self):
        # explicitly delete the file, since it is not done automagically by django
        # TODO - make this a bit cleaner.
        if StagingClasslistCSV.objects.exists():
            Path(StagingClasslistCSV.objects.get().csv_file.path).unlink()
            StagingClasslistCSV.objects.filter().delete()


class StagingStudentService:
    @transaction.atomic
    def how_many_students(self):
        return StagingStudent.objects.all().count()

    @transaction.atomic
    def are_there_students(self):
        return StagingStudent.objects.exists()

    @transaction.atomic()
    def get_students(self):
        return list(
            StagingStudent.objects.all().values(
                "student_id", "student_name", "paper_number"
            )
        )

    def get_classdict(self):
        students = self.get_students()
        for s in students:
            s["id"] = s.pop("student_id")
            s["studentName"] = s.pop("student_name")
            if s["paper_number"] is None:
                s["paper_number"] = -1
        return students

    @transaction.atomic()
    def get_first_last_prenamed_paper(self):
        query = StagingStudent.objects.filter(paper_number__isnull=False).order_by(
            "paper_number"
        )
        if query.exists():
            return (query.first().paper_number, query.last().paper_number)
        else:
            return (None, None)

    @transaction.atomic()
    def get_prenamed_papers(self):
        """Return dict of prenamed papers {paper_number: (student_id, student_name)}."""
        return {
            s_obj.paper_number: (s_obj.student_id, s_obj.student_name)
            for s_obj in StagingStudent.objects.filter(paper_number__isnull=False)
        }

    def get_students_as_csv_string(self, prename=False):
        # Write the data from the staging-students table into a string in simple CSV format
        # make sure header and name-column are quoted
        # and make sure the paper_number column is -1 if not pre-naming.
        txt = '"id", "name", "paper_number"\n'
        for row in self.get_students():
            if prename and row["paper_number"]:
                txt += f"{row['student_id']}, \"{row['student_name']}\", {row['paper_number']}\n"
            else:
                # don't print the -1 for non-prename.
                txt += f"{row['student_id']}, \"{row['student_name']}\", \n"
        return txt

    @transaction.atomic()
    def add_student(self, student_id, student_name, paper_number=None):
        # will raise an integrity error if id not unique

        s_obj = StagingStudent(student_id=student_id, student_name=student_name)
        # set the paper_number if present
        if paper_number:
            s_obj.paper_number = paper_number
        s_obj.save()

    @transaction.atomic()
    def remove_all_students(self):
        StagingStudent.objects.all().delete()

    @transaction.atomic()
    def use_classlist_csv(self):
        scsv = StagingClasslistCSVService()
        classlist_csv = scsv.get_classlist_csv_filepath()
        with open(classlist_csv) as fh:
            csv_reader = csv.DictReader(fh, skipinitialspace=True)
            # make sure headers are lowercase
            old_headers = csv_reader.fieldnames
            # since this has been validated we know it has 'id', 'name', 'paper_number'
            csv_reader.fieldnames = [x.lower() for x in old_headers]
            # now we have lower case field names
            for row in csv_reader:
                self.add_student(row["id"], row["name"], row["paper_number"])
        # after used make sure the csv is deleted
        scsv.delete_classlist_csv()

    @transaction.atomic()
    def get_minimum_number_to_produce(self):
        # if no students then return 20
        # N = number of students in classlist
        # L = last prenamed paper in classlist
        # else compute max of { 1.1*N, N+20, L+10 } - make sure integer.
        if not self.are_there_students():
            return 20

        N = self.how_many_students()
        N1 = -(
            (-N * 11) // 10
        )  # simple fiddle to get ceiling of 1.1*N using python floor-div //
        N2 = N + 20

        pss = PrenameSettingService()
        if pss.get_prenaming_setting():
            first_prename, last_prename = self.get_first_last_prenamed_paper()
            N3 = last_prename + 10
            return max(N1, N2, N3)
        else:
            return max(N1, N2)

    def get_classlist_sids_for_ID_matching(self):
        """Returns a list containing all student IDs on the classlist."""
        students = []
        classlist = self.get_students()
        for entry in classlist:
            students.append(entry.pop("student_id"))
        return students

    def get_prename_for_paper(self, paper_number):
        """Return student ID for prenamed paper or None if paper is not prenamed."""
        try:
            student_obj = StagingStudent.objects.get(paper_number=paper_number)
            return student_obj.student_id
        except ObjectDoesNotExist:
            return None

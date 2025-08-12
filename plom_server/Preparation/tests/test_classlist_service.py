# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

import codecs
import tempfile
from pathlib import Path

from django.test import TestCase

from ..services import StagingStudentService as Service


class TestClasslistService(TestCase):
    """Test the classlist service validate_and_use_classlist_csv.

    Note Vlad the validator also has its own tests in plom/create/test_classlist.py.
    """

    def test_basic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            with tmpfile.open("w") as f:
                f.write('"id","name"\n')
                f.write('12345677,"Doe, Ursula"\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertTrue(success)
            self.assertListEqual(warn_err, [])
        self.assertEqual(Service.how_many_students(), 1)
        Service.remove_all_students()
        self.assertEqual(Service.how_many_students(), 0)

    def test_appending_a_student(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            with tmpfile.open("w") as f:
                f.write('"id","name"\n')
                f.write('12345677,"Uno, Ursula"\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertTrue(success)
            self.assertEqual(Service.how_many_students(), 1)

            with tmpfile.open("w") as f:
                f.write('"id","name"\n')
                f.write('12345678,"Dos, Damian"\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertTrue(success)
            self.assertEqual(Service.how_many_students(), 2)

    def test_append_atomic_insertion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            with tmpfile.open("w") as f:
                f.write('"id","name"\n')
                f.write('11111111,"Uno, Ursula"\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertTrue(success)
            self.assertEqual(Service.how_many_students(), 1)

            with tmpfile.open("w") as f:
                f.write('"id","name"\n')
                f.write('22222222,"Dos, Damian"\n')
                f.write('11111111,"Duplicate will cause collision"\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertFalse(success)
            self.assertTrue("collides" in warn_err[0]["werr_text"])
            # But neither student was added: still just original classlist
            self.assertEqual(Service.how_many_students(), 1)

    def test_degenerate_classlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            with tmpfile.open("w") as f:
                f.write('"id","name"\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertTrue(success)
            (row,) = warn_err
            self.assertEqual(row["warn_or_err"], "warn")
            self.assertTrue("empty" in row["werr_text"])
            self.assertEqual(Service.how_many_students(), 0)

    def test_degenerate_classlist_headers_still_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            with tmpfile.open("w") as f:
                f.write('"id","namez"\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertFalse(success)
            self.assertTrue("Missing 'name'" in warn_err[0]["werr_text"])
            self.assertEqual(Service.how_many_students(), 0)

    def test_classlist_duplicates_papernum(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            with tmpfile.open("w") as f:
                f.write('"id","name","paper_number"\n')
                f.write('11111111,"Uno, Ursula",11\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertTrue(success)
            self.assertEqual(Service.how_many_students(), 1)

            with tmpfile.open("w") as f:
                f.write('"id","name","paper_number"\n')
                f.write('22222222,"Dos, Damian",12\n')
                f.write('33333333,"Duplicating papernum",11\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertFalse(success)
            self.assertTrue("duplicates 1 paper number" in warn_err[0]["werr_text"])
            # Atomic: neither new student was added
            self.assertEqual(Service.how_many_students(), 1)

    def test_duplicate_IDs_in_one_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            with tmpfile.open("w") as f:
                f.write('"id","name"\n')
                f.write('11111111,"Uno, Ursula"\n')
                f.write('22222222,"Dos, Damian"\n')
                f.write('11111111,"Tres, SameID"\n')
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertFalse(success)
            (row,) = warn_err
            self.assertTrue("'11111111' is used multiple" in row["werr_text"])

    def test_feffid_bom_classlist_issue_3200(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            # tmpfile = Path("/home/cbm") / "foo.csv"
            with tmpfile.open("wb") as f:
                f.write(codecs.BOM_UTF8)
                f.write("id,name\n".encode("utf8"))
                f.write('11111111,"Doe, 学生"\n'.encode("utf8"))
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertTrue(success)
            self.assertListEqual(warn_err, [])
        (row,) = Service.get_students()
        self.assertEqual(row["student_name"], "Doe, 学生")

    def test_misdetected_dialect_bom_crlf_issue_3938(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            # tmpfile = Path("/home/cbm") / "foo.csv"
            with tmpfile.open("wb") as f:
                f.write(codecs.BOM_UTF8)
                f.write("id,name\r\n".encode("utf8"))
                f.write('11111111,"Comma, Separated"\r\n'.encode("utf8"))
                f.write('12121212,"Lastname, Firstname"\r\n'.encode("utf8"))
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertTrue(success)
            self.assertListEqual(warn_err, [])

    def test_misdetected_dialect_bom_crlf_issue_3938_example2(self) -> None:
        # This looks similar to the previous test, but the old sniffer-based code
        # would fail differently: I think it detect "e" as the separator here.
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "foo.csv"
            # tmpfile = Path("/home/cbm") / "foo.csv"
            with tmpfile.open("wb") as f:
                f.write(codecs.BOM_UTF8)
                f.write("id,name\r\n".encode("utf8"))
                f.write('11223344,"Meh, Foo"\r\n'.encode("utf8"))
                f.write('44332211,"Meh, Bar"\r\n'.encode("utf8"))
            with tmpfile.open("rb") as f:
                success, warn_err = Service.validate_and_use_classlist_csv(f)
            self.assertTrue(success)
            self.assertListEqual(warn_err, [])

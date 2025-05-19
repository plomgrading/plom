# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

import tempfile
from pathlib import Path

from django.test import TestCase

from ..services import StagingStudentService as Service


class TestClasslistService(TestCase):
    """Test the classlist service valdiate_and_use_classlist_csv.

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
            # TODO: or should we generate a warning here?
            assert warn_err == []
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

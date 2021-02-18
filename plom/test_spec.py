# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

from pytest import raises
from plom import SpecVerifier


def test_spec_demo():
    s = SpecVerifier.demo()
    assert s.number_to_name
    assert s.number_to_produce


def test_spec_verify():
    s = SpecVerifier.demo()
    s.verifySpec(verbose=False)


def test_spec_too_many_named():
    s = SpecVerifier.demo()
    s.spec["numberToProduce"] = 50
    s.spec["numberToName"] = 60
    raises(ValueError, lambda: s.verifySpec(verbose=False))


def test_spec_negatives_still_pass():
    s = SpecVerifier.demo()
    s.spec["numberToName"] = -1
    s.spec["numberToProduce"] = -1
    s.verifySpec(verbose=False)


def test_spec_setting_adds_spares():
    s = SpecVerifier.demo()
    s.spec["numberToName"] = -1
    s.spec["numberToProduce"] = -1
    s.set_number_papers_to_name(16)
    s.set_number_papers_add_spares(16)
    assert s.number_to_name == 16
    assert s.number_to_produce > 16
    s.verifySpec(verbose=False)


def test_spec_invalid_shortname():
    s = SpecVerifier.demo()
    s.spec["name"] = "no spaces"
    raises(ValueError, lambda: s.verifySpec(verbose=False))


def test_spec_too_many_named():
    s = SpecVerifier.demo()
    s.spec["numberToProduce"] = 50
    s.spec["numberToName"] = 60
    raises(ValueError, lambda: s.verifySpec(verbose=False))

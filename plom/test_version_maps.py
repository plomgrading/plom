# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

import json

from pytest import raises

from plom import make_random_version_map, check_version_map
from plom import undo_json_packing_of_version_map
from plom import SpecVerifier


def test_make_rand_ver_map():
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    check_version_map(vm)
    check_version_map(vm, spec)


def test_ver_map_fails_if_too_short():
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm.pop(1)
    check_version_map(vm)  # passes if we don't know spec
    raises(AssertionError, lambda: check_version_map(vm, spec))


def test_ver_map_types():
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm["1"] = vm.pop(1)
    raises(AssertionError, lambda: check_version_map(vm))


def test_ver_map_types2():
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1] = 42
    raises(AssertionError, lambda: check_version_map(vm))


def test_ver_map_types3():
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1]["2"] = vm[1].pop(2)
    raises(AssertionError, lambda: check_version_map(vm))


def test_ver_map_types4():
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1][2] = "str"
    raises(AssertionError, lambda: check_version_map(vm))


def test_ver_map_verions_in_range():
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1][1] = -1
    raises(AssertionError, lambda: check_version_map(vm))
    vm[1][1] = spec["numberOfQuestions"] + 1
    raises(AssertionError, lambda: check_version_map(vm, spec))


def test_ver_map_fix_has_ver1_only():
    # assumes version 2 is fixed in demo: test will need adjusting if that changes
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1][2] = 2
    raises(AssertionError, lambda: check_version_map(vm, spec))


def test_ver_map_json_roundtrip():
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    s = json.dumps(vm)
    vm2 = json.loads(s)
    assert vm != vm2  # I mean, we'd like, but Json doesn't
    vm3 = undo_json_packing_of_version_map(vm2)
    assert vm == vm3


def test_ver_map_check_spec_or_dict():
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm.pop(1)
    raises(AssertionError, lambda: check_version_map(vm, spec))
    raises(AssertionError, lambda: check_version_map(vm, spec.get_public_spec_dict()))


def test_ver_map_from_dict():
    spec = SpecVerifier.demo()
    spec.verify()
    spec_dict = spec.get_public_spec_dict()
    vm = make_random_version_map(spec_dict)
    check_version_map(vm, spec_dict)
    check_version_map(vm, spec)

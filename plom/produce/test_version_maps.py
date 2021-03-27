# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

from pytest import raises

from plom.produce import make_random_version_map, check_version_map
from plom import SpecVerifier


def test_make_rand_ver_map():
    spec = SpecVerifier.demo()
    vm = make_random_version_map(spec)
    check_version_map(vm)
    check_version_map(vm, spec)


def test_ver_map_fails_if_too_short():
    spec = SpecVerifier.demo()
    vm = make_random_version_map(spec)
    vm.pop(1)
    check_version_map(vm)  # passes if we don't know spec
    raises(AssertionError, lambda: check_version_map(vm, spec))


def test_ver_map_check_spec_or_dict():
    spec = SpecVerifier.demo()
    vm = make_random_version_map(spec)
    vm.pop(1)
    raises(AssertionError, lambda: check_version_map(vm, spec))
    raises(AssertionError, lambda: check_version_map(vm, spec.get_public_spec_dict()))


def test_ver_map_from_dict():
    spec = SpecVerifier.demo()
    spec_dict = spec.get_public_spec_dict()
    vm = make_random_version_map(spec_dict)
    check_version_map(vm, spec_dict)
    check_version_map(vm, spec)

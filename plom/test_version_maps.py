# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021, 2023-2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

import json

from pytest import raises

from plom.spec_verifier import SpecVerifier
from plom.version_maps import (
    check_version_map,
    make_random_version_map,
    undo_json_packing_of_version_map,
)


def test_make_rand_ver_map() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    check_version_map(vm)
    check_version_map(vm, spec)


def test_ver_map_legacy_fails_if_too_short() -> None:
    # likely legacy specific: remove?
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm.pop(spec["numberToProduce"])
    check_version_map(vm)  # passes if we don't know spec
    with raises(ValueError, match="number of rows"):
        check_version_map(vm, spec, legacy=True)


def test_ver_map_legacy_fails_if_non_contiguous() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    maxkey = max(vm.keys())
    vm.pop(maxkey // 2)
    with raises(ValueError, match="gap"):
        check_version_map(vm, legacy=True)


def test_ver_map_legacy_fails_if_not_start_at_1() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm.pop(1)
    with raises(ValueError, match="start"):
        check_version_map(vm, legacy=True)


def test_ver_map_types() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm["1"] = vm.pop(1)  # type: ignore
    with raises(ValueError, match="paper number.*integer"):
        check_version_map(vm)


def test_ver_map_types2() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1] = 42  # type: ignore
    with raises(ValueError, match="row.*dict"):
        check_version_map(vm)


def test_ver_map_types3() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1]["2"] = vm[1].pop(2)  # type: ignore
    with raises(ValueError, match="question.*integer"):
        check_version_map(vm)


def test_ver_map_types4() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1][2] = "str"  # type: ignore
    with raises(ValueError, match="version.*integer"):
        check_version_map(vm)


def test_ver_map_verions_in_range() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1][1] = -1
    with raises(ValueError, match="positive"):
        check_version_map(vm)
    vm[1][1] = spec["numberOfVersions"] + 1
    with raises(ValueError, match="number of versions"):
        check_version_map(vm, spec)


def test_ver_map_id_verions() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    for t, row in vm.items():
        row["id"] = (t % 2) + 1
    check_version_map(vm)


def test_ver_map_id_verions_in_range() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1]["id"] = -1
    with raises(ValueError, match="positive"):
        check_version_map(vm)
    vm[1]["id"] = spec["numberOfVersions"] + 1
    with raises(ValueError, match="number of versions"):
        check_version_map(vm, spec)


def test_ver_map_fix_has_ver1_only() -> None:
    # assumes version 2 is fixed in demo: test will need adjusting if that changes
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    vm[1][2] = 2
    with raises(ValueError, match='not in question\'s "select"'):
        check_version_map(vm, spec)


def test_ver_map_json_roundtrip() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    s = json.dumps(vm)
    vm2 = json.loads(s)
    assert vm != vm2  # I mean, we'd like, but Json doesn't
    vm3 = undo_json_packing_of_version_map(vm2)
    assert vm == vm3


def test_ver_map_check_spec_or_dict() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    vm = make_random_version_map(spec)
    check_version_map(vm, spec)
    check_version_map(vm, spec.get_public_spec_dict())


def test_ver_map_from_dict() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    spec_dict = spec.get_public_spec_dict()
    vm = make_random_version_map(spec_dict)
    check_version_map(vm, spec_dict)
    check_version_map(vm, spec)


def test_ver_map_reproducible() -> None:
    spec = SpecVerifier.demo()
    spec.verify()
    spec_dict = spec.spec
    spec_dict["numberOfVersions"] = 5
    spec_dict["numberToProduce"] = 6
    vm = make_random_version_map(spec_dict, seed="plom")
    saved_vm = {
        1: {1: 2, 2: 1, 3: 1},
        2: {1: 2, 2: 1, 3: 2},
        3: {1: 1, 2: 1, 3: 1},
        4: {1: 5, 2: 1, 3: 2},
        5: {1: 4, 2: 1, 3: 2},
        6: {1: 3, 2: 1, 3: 1},
    }
    assert vm == saved_vm

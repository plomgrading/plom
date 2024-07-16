# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

from django.db import transaction

from plom import SpecVerifier
from plom.version_maps import version_map_to_csv

from Papers.services import SpecificationService

from ..services import StagingStudentService


class PQVMappingService:
    # Note that this service should not modify the database
    # It should now simply construct qvmaps in various forms
    # and know how to read the paper-database to get pqv info

    @transaction.atomic()
    def get_pqv_map_dict(self) -> dict[int, dict[int, int]]:
        from Papers.services import PaperInfoService

        return PaperInfoService().get_pqv_map_dict()

    def get_pqv_map_as_table(
        self, prenaming: bool = False
    ) -> dict[int, dict[str, Any]]:
        # format the data in a way that makes it easy to display for django-template
        # in particular, a dict of lists.
        pqvmapping = self.get_pqv_map_dict()
        pqv_table = {}
        question_indices = SpecificationService.get_question_indices()

        for paper_number, qvmap in sorted(pqvmapping.items()):
            pqv_table[paper_number] = {
                "prename": None,
                "qvlist": [qvmap[q] for q in question_indices],
            }

            # if prenaming then we need to put in those student details
        if prenaming:
            sss = StagingStudentService()
            for paper_number, student in sss.get_prenamed_papers().items():
                if paper_number in pqv_table:
                    pqv_table[paper_number]["prename"] = student
                else:
                    # TODO - issue a warning - means we are trying to prename a
                    # paper for which we do not have a qvmap.
                    pass
        return pqv_table

    @transaction.atomic()
    def pqv_map_to_csv(self, f: Path) -> None:
        pqvmap = self.get_pqv_map_dict()
        version_map_to_csv(pqvmap, f, _legacy=False)

    @transaction.atomic()
    def get_pqv_map_as_csv_string(self):
        # non-ideal implementation, but version_map_to_csv does not speak to a BytesIO
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "file.csv"
            self.pqv_map_to_csv(f)
            with open(f, "r") as fh:
                txt = fh.readlines()
            return txt

    def make_version_map(self, numberToProduce: int, *, first: int = 1):
        """Generate a paper-question-version-map.

        Args:
            numberToProduce: how many items in the version map.

        Keyword Args:
            first: the starting paper number.

        Return:
            dict: a dict-of-dicts keyed by paper number (int) and then
            question number (int, but indexed from 1 not 0).  Values are
            integers.

        """
        from plom import make_random_version_map

        # grab the spec as dict from the test creator services
        spec_dict = SpecificationService.get_the_spec()
        # Legacy make_random_version_map will be unhappy if not fed a numberToProduce
        # so we add one.
        # this spec_dict does not include numberToProduce so we add it
        spec_dict["numberToProduce"] = numberToProduce

        # now pass it through spec verifier and feed the **verifier** to the
        # qv-map creator
        speck = SpecVerifier(spec_dict)

        seed = SpecificationService.get_private_seed()
        pqvmap = make_random_version_map(speck, seed=seed)
        # kind of hacky: we just increase/decrease the keys
        pqvmap = {k - 1 + first: v for k, v in pqvmap.items()}
        # bit of a hack to ensure versions match per page
        return _fix_shared_pages(pqvmap)

    def get_minimum_number_to_produce(self):
        sss = StagingStudentService()
        return sss.get_minimum_number_to_produce()


def _fix_shared_pages(vmap):
    # Ensure any questions that share pages match versions.
    # TODO: a read-only checker for this would be useful; at least a warning for self-uploaded
    spec = SpecificationService.get_the_spec()
    for q in reversed(SpecificationService.get_question_indices()):
        # TODO: still don't like these str(qidx)
        my_pages = spec["question"][str(q)]["pages"]
        for pg in my_pages:
            for qidx_str, v in spec["question"].items():
                qidx = int(qidx_str)  # yuck, well this whole fcn but especially this
                if qidx_str == str(q):
                    continue
                if pg in v["pages"]:
                    # we are sharing a page with an earlier (b/c reverse) question
                    # so copy all those versions
                    for paper in vmap.keys():
                        vmap[paper][q] = vmap[paper][qidx]
    return vmap

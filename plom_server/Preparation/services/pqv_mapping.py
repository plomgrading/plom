# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

from django.db import transaction

from plom import SpecVerifier
from plom.version_maps import version_map_to_csv, check_version_map

from Papers.services import SpecificationService

from ..models import StagingPQVMapping
from ..services import StagingStudentService, PapersPrinted


class PQVMappingService:
    @transaction.atomic()
    def is_there_a_pqv_map(self):
        return StagingPQVMapping.objects.exists()

    @transaction.atomic()
    def list_of_paper_numbers(self):
        paper_numbers = [
            x
            for x in StagingPQVMapping.objects.values_list("paper_number", flat=True)
            .order_by("paper_number")
            .distinct()
        ]
        return paper_numbers

    @transaction.atomic()
    def remove_pqv_map(self) -> None:
        """Erase the question-version map.

        Raises:
            ValueError: cannot erase for example b/c papers already printed.
        """
        # TODO: better more precise logic to protect this?
        if PapersPrinted.have_papers_been_printed():
            raise ValueError(
                "You cannot erase the QV map b/c you indicated papers have been printed"
            )
        StagingPQVMapping.objects.all().delete()

    @transaction.atomic()
    def use_pqv_map(self, pqvmap: dict[int, dict[int, int]]):
        """Populate the database with this particular version map.

        Note: assumes that there is no current pqvmap or that you are adding
        to the existing pqvmap.

        Raises:
            ValueError: invalid map.
        """
        check_version_map(pqvmap, spec=SpecificationService.get_the_spec())
        for paper_number, qvmap in pqvmap.items():
            for question, version in qvmap.items():
                StagingPQVMapping.objects.create(
                    paper_number=paper_number, question=question, version=version
                )

    @transaction.atomic()
    def get_pqv_map_dict(self) -> dict[int, dict[int, int]]:
        # put into the dict in paper_number order.
        pqvmapping: dict[int, dict[int, int]] = {}
        for pqv_obj in StagingPQVMapping.objects.all().order_by("paper_number"):
            if pqv_obj.paper_number in pqvmapping:
                pqvmapping[pqv_obj.paper_number][pqv_obj.question] = pqv_obj.version
            else:
                pqvmapping[pqv_obj.paper_number] = {pqv_obj.question: pqv_obj.version}

        return pqvmapping

    @transaction.atomic()
    def get_pqv_map_length(self) -> int:
        # TODO: likely not the most efficient way!
        return len(self.get_pqv_map_dict())
        # But careful, its certainly not this:
        # return StagingPQVMapping.objects.count()

    def get_pqv_map_as_table(
        self, prenaming: bool = False
    ) -> dict[int, dict[str, Any]]:
        # format the data in a way that makes it easy to display for django-template
        # in particular, a dict of lists.
        pqvmapping = self.get_pqv_map_dict()
        pqv_table = {}
        question_indices = SpecificationService.get_question_indices()

        for paper_number, qvmap in pqvmapping.items():
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

    def make_version_map(self, numberToProduce):
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
        return make_random_version_map(speck, seed=seed)

    def generate_and_set_pqvmap(
        self, number_to_produce: int, *, first: int = 1
    ) -> None:
        """Remove any existing question-version map, generate a new map and set it in the database.

        Args:
            number_to_produce: how many items in the version map.

        Keyword Args:
            first: the starting paper number.

        Returns:
            None
        """
        self.remove_pqv_map()
        pqvmap = self.make_version_map(number_to_produce)
        # kind of hacky: we just increase/decrease the keys
        pqvmap = {k - 1 + first: v for k, v in pqvmap.items()}
        # bit of a hack to ensure versions match per page
        pqvmap = _fix_shared_pages(pqvmap)
        self.use_pqv_map(pqvmap)

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

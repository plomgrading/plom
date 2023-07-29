# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.db import transaction

from plom import SpecVerifier
from Papers.services import SpecificationService

from ..models import StagingPQVMapping
from ..services import StagingStudentService


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
    def remove_pqv_map(self):
        StagingPQVMapping.objects.all().delete()

    @transaction.atomic()
    def use_pqv_map(self, valid_pqvmap):
        # assumes that there is no current pqvmap.
        # assumes that passed pqvmap is valid
        for paper_number, qvmap in valid_pqvmap.items():
            for question, version in qvmap.items():
                StagingPQVMapping.objects.create(
                    paper_number=paper_number, question=question, version=version
                )

    @transaction.atomic()
    def get_pqv_map_dict(self):
        pqvmapping = {}
        for pqv_obj in StagingPQVMapping.objects.all():
            if pqv_obj.paper_number in pqvmapping:
                pqvmapping[pqv_obj.paper_number][pqv_obj.question] = pqv_obj.version
            else:
                pqvmapping[pqv_obj.paper_number] = {pqv_obj.question: pqv_obj.version}

        return pqvmapping

    @transaction.atomic()
    def get_pqv_map_length(self):
        # TODO: likely not the most efficient way!
        return len(self.get_pqv_map_dict())
        # But careful, its certainly not this:
        # return StagingPQVMapping.objects.count()

    def get_pqv_map_as_table(self, prenaming=False):
        # format the data in a way that makes it easy to display for django-template
        # in particular, a dict of lists.
        pqvmapping = self.get_pqv_map_dict()
        pqv_table = {}
        speck = SpecificationService()
        question_list = [
            q + 1 for q in range(speck.get_n_questions())
        ]  # todo - replace with spec lookup

        for paper_number, qvmap in pqvmapping.items():
            pqv_table[paper_number] = {
                "prename": None,
                "qvlist": [qvmap[q] for q in question_list],
            }

            # if prenaming then we need to put in those student details
        if prenaming:
            sss = StagingStudentService()
            for paper_number, student in sss.get_prenamed_papers().items():
                pqv_table[paper_number]["prename"] = student
        return pqv_table

    @transaction.atomic()
    def get_pqv_map_as_csv(self):
        pqvmap = self.get_pqv_map_dict()
        speck = SpecificationService()
        qlist = [q + 1 for q in range(speck.get_n_questions())]
        # TODO - replace this with some python csv module stuff
        txt = '"paper_number"'
        for q in qlist:
            txt += f', "q{q}.version"'
        txt += "\n"
        for paper_number, qvmap in pqvmap.items():
            txt += f"{paper_number}"
            for q, v in qvmap.items():
                txt += f", {v}"
            txt += "\n"
        return txt

    def make_version_map(self, numberToProduce):
        from plom import make_random_version_map

        # grab the spec as dict from the test creator services
        speck = SpecificationService()
        spec_dict = speck.get_the_spec()
        # Legacy make_random_version_map will be unhappy if not fed a numberToProduce
        # so we add one.
        # this spec_dict does not include numberToProduce so we add it
        spec_dict["numberToProduce"] = numberToProduce

        # now pass it through spec verifier and feed the **verifier** to the
        # qv-map creator
        speck = SpecVerifier(spec_dict)

        return make_random_version_map(speck)

    def generate_and_set_pqvmap(self, numberToProduce):
        # delete old map, build a new one, and then use it.
        self.remove_pqv_map()
        pqvmap = self.make_version_map(numberToProduce)
        self.use_pqv_map(pqvmap)

    def get_minimum_number_to_produce(self):
        sss = StagingStudentService()
        return sss.get_minimum_number_to_produce()

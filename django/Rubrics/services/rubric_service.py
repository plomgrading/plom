# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2010-2023 Colin B. Macdonald
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Nicholas J H Lai

import logging

from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError

from Rubrics.serializers import RelativeRubricSerializer, NeutralRubricSerializer
from Rubrics.models import NeutralRubric, RelativeRubric, RubricPane


log = logging.getLogger("RubricServer")


class RubricService:
    """
    Class to encapsulate functions for creating and modifying rubrics.
    """

    def create_rubric(self, rubric_data):
        """
        Create a rubric using data submitted by a marker.

        Args:
            rubric_data: (dict) data for a rubric submitted by a web request.

        Returns:
            Rubric: the created and saved rubric instance.
        """

        # TODO: add a function to check if a rubric_data is valid/correct
        self.check_rubric(rubric_data)

        username = rubric_data.pop("username")
        user = User.objects.get(username=username)
        rubric_data["user"] = user.pk

        kind = rubric_data["kind"]

        if kind == "relative":
            serializer = RelativeRubricSerializer(data=rubric_data)
            serializer.is_valid()
            serializer.save()
            rubric = serializer.instance
        elif kind == "neutral":
            serializer = NeutralRubricSerializer(data=rubric_data)
            serializer.is_valid()
            serializer.save()
            rubric = serializer.instance
        else:
            assert False, "We've got a problem creating rubric."

        return rubric

    def modify_rubric(self, key, rubric_data):
        """
        Modify a rubric.

        Args:
            key: (str) a sequence of ints representing
            rubric_data: (dict) data for a rubric submitted by a web request.

        Returns:
            Rubric: the modified rubric instance.
        """

        username = rubric_data.pop("username")
        user = User.objects.get(
            username=username
        )  # TODO: prevent different users from modifying rubrics?
        rubric_data["user"] = user.pk

        kind = rubric_data["kind"]

        if kind == "relative":
            rubric = RelativeRubric.objects.get(key=key)
            serializer = RelativeRubricSerializer(rubric, data=rubric_data)
            serializer.is_valid()
            serializer.save()
            rubric_instance = serializer.instance
        elif kind == "neutral":
            rubric = NeutralRubric.objects.get(key=key)
            serializer = NeutralRubricSerializer(rubric, data=rubric_data)
            serializer.is_valid()
            serializer.save()
            rubric_instance = serializer.instance
        else:
            assert False, "We've got a problem modifying rubric."

        return rubric_instance

    def get_rubrics(self, *, question=None):
        """
        Get the rubrics, possibly filtered by question number

        Args:
            question: (None/str) question number or None for all.

        Returns:
            list: dictionaries, one for each rubric.
        """
        if question is None:
            neutral_rubric_list = NeutralRubric.objects.all()
            relative_rubric_list = RelativeRubric.objects.all()
        else:
            neutral_rubric_list = NeutralRubric.objects.filter(question=question)
            relative_rubric_list = RelativeRubric.objects.filter(question=question)
        rubric_data = []

        for neutral_rubric in neutral_rubric_list:
            neutral_rubric_dict = {
                "id": neutral_rubric.key,
                "kind": neutral_rubric.kind,
                "display_delta": neutral_rubric.display_delta,
                "value": neutral_rubric.value,
                "out_of": neutral_rubric.out_of,
                "text": neutral_rubric.text,
                "tags": neutral_rubric.tags,
                "meta": neutral_rubric.meta,
                "username": neutral_rubric.user.username,
                "question": neutral_rubric.question,
                "versions": neutral_rubric.versions,
                "parameters": neutral_rubric.parameters,
            }
            rubric_data.append(neutral_rubric_dict)

        for relative_rubric in relative_rubric_list:
            relative_rubric_dict = {
                "id": relative_rubric.key,
                "kind": relative_rubric.kind,
                "display_delta": relative_rubric.display_delta,
                "value": relative_rubric.value,
                "out_of": relative_rubric.out_of,
                "text": relative_rubric.text,
                "tags": relative_rubric.tags,
                "meta": relative_rubric.meta,
                "username": relative_rubric.user.username,
                "question": relative_rubric.question,
                "versions": relative_rubric.versions,
                "parameters": relative_rubric.parameters,
            }
            rubric_data.append(relative_rubric_dict)

        return rubric_data

    def init_rubrics(self):
        """Add special rubrics such as deltas and per-question specific.

        Returns:
            bool: true if initialized or False if it was already initialized.
        """
        rubrics1 = NeutralRubric.objects.all()
        rubrics2 = RelativeRubric.objects.all()
        # rubrics3 = AbsoluteRubric.objects.all()
        if rubrics1 or rubrics2:  # or rubrics3:
            return False
        # TODO: stop hardcoding!
        spec = {"numberOfQuestions": 3}
        spec["question"] = {"1": {"mark": 5}, "2": {"mark": 5}, "3": {"mark": 10}}
        self._build_special_rubrics(spec)
        return True

    def _build_special_rubrics(self, spec):
        log.info("Building special manager-generated rubrics")
        # create standard manager delta-rubrics - but no 0, nor +/- max-mark
        for q in range(1, 1 + spec["numberOfQuestions"]):
            mx = spec["question"]["{}".format(q)]["mark"]
            # make zero mark and full mark rubrics
            rubric = {
                "kind": "absolute",
                "display_delta": f"0 of {mx}",
                "value": "0",
                "out_of": mx,
                "text": "no answer given",
                "question": q,
                "meta": "Is this answer blank or nearly blank?  Please do not use "
                + "if there is any possibility of relevant writing on the page.",
                "tags": "",
                "username": "manager",
            }
            try:
                r = self.create_rubric(rubric)
            except AssertionError:
                print("Skippping absolute rubric, not implemented yet, Issue #2641")
            # log.info("Built no-answer-rubric Q%s: key %s", q, r.pk)

            rubric = {
                "kind": "absolute",
                "display_delta": f"0 of {mx}",
                "value": "0",
                "out_of": mx,
                "text": "no marks",
                "question": q,
                "meta": "There is writing here but its not sufficient for any points.",
                "tags": "",
                "username": "manager",
            }
            try:
                r = self.create_rubric(rubric)
            except AssertionError:
                print("Skippping absolute rubric, not implemented yet, Issue #2641")
            # log.info("Built no-marks-rubric Q%s: key %s", q, r.pk)

            rubric = {
                "kind": "absolute",
                "display_delta": f"{mx} of {mx}",
                "value": f"{mx}",
                "out_of": mx,
                "text": "full marks",
                "question": q,
                "meta": "",
                "tags": "",
                "username": "manager",
            }
            try:
                r = self.create_rubric(rubric)
            except AssertionError:
                print("Skippping absolute rubric, not implemented yet, Issue #2641")
            # log.info("Built full-marks-rubric Q%s: key %s", q, r.pk)

            # now make delta-rubrics
            for m in range(1, mx + 1):
                # make positive delta
                rubric = {
                    "display_delta": "+{}".format(m),
                    "value": m,
                    "out_of": 0,
                    "text": ".",
                    "kind": "relative",
                    "question": q,
                    "meta": "",
                    "tags": "",
                    "username": "manager",
                }
                r = self.create_rubric(rubric)
                log.info("Built delta-rubric +%d for Q%s: %s", m, q, r.pk)
                # make negative delta
                rubric = {
                    "display_delta": "-{}".format(m),
                    "value": -m,
                    "out_of": 0,
                    "text": ".",
                    "kind": "relative",
                    "question": q,
                    "meta": "",
                    "tags": "",
                    "username": "manager",
                }
                r = self.create_rubric(rubric)
                log.info("Built delta-rubric -%d for Q%s: %s", m, q, r.pk)

    def erase_all_rubrics(self):
        """
        Remove all rubrics, permanently deleting them.  BE CAREFUL.

        Returns:
            int: how many rubrics were removed.
        """
        n = 0
        neutral_rubric_list = NeutralRubric.objects.all()
        for r in neutral_rubric_list:
            r.delete()
            n += 1
        relative_rubric_list = RelativeRubric.objects.all()
        for r in relative_rubric_list:
            r.delete()
            n += 1
        return n

    def get_rubric_pane(self, user, question):
        """
        Gets a rubric pane for a user.

        Args:
            user: a User instance
            question: (int)

        Returns:
            dict: the JSON representation of the pane.
        """

        pane, created = RubricPane.objects.get_or_create(user=user, question=question)
        if created:
            return {}
        return pane.data

    def update_rubric_pane(self, user, question, data):
        """
        Updates a rubric pane for a user.

        Args:
            user: a User instance
            question: int
            data: dict representing the new pane
        """

        pane = RubricPane.objects.get(user=user, question=question)
        pane.data = data
        pane.save()

    def check_rubric(self, rubric_data):
        """
        Check rubric data to ensure the data is consistent.

        Args:
            rubric_data: (dict) data for a rubric submitted by a web request.
        """
        # if rubric_data["kind"] not in ["relative", "neutral", "absolute"]:
        #     raise ValidationError(f"Unrecognised rubric kind: {rubric_data.kind}")
        pass

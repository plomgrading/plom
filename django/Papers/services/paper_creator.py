from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, IntegrityError

from Papers.models import Specification, Paper, IDGroup, DNMGroup, QuestionGroup

import logging

log = logging.getLogger("PaperCreatorService")


class PaperCreatorService:
    """Class to encapsulate all the functions to build the test-papers and
    groups in the db. DB must have a validated test spec before we can use
    this.
    """

    def __init__(self):
        try:
            self.spec = Specification.load().spec_dict
        except Specification.DoesNotExist:
            raise ObjectDoesNotExist(
                "The database does not contain a test specification."
            )

    @transaction.atomic
    def create_paper_with_qvmapping(self, paper_number, qv_mapping):
        """Creates a paper with the given paper number and the given
        question-version mapping.

        paper_number (int): The number of the paper being created
        qv_mapping (dict): Mapping from each question-number to
            version for this particular paper. Of the form {q: v}

        """
        # TODO - on successful build, we should add a
        # "we-need-to-build-a-pdf-for-this-paper" task
        # so that the user can (later) build it in the background
        # via huey or similar.

        # First build the paper itself
        paper_obj = Paper(paper_number=paper_number)
        try:
            paper_obj.save()
        except IntegrityError as err:
            log.warn(f"Cannot create Paper {paper_number}: {err}")
            raise IntegrityError(
                f"An entry paper {paper_number} already exists in the database"
            )
        # Now build its groups - IDGroup, DNMGroup, QuestionGroups
        gid = "{}i".format(str(paper_number).zfill(4))
        idgroup_obj = IDGroup(
            paper=paper_obj, gid=gid, expected_number_pages=1, complete=False
        )
        try:
            idgroup_obj.save()
        except IDGroup.IntegrityError as err:
            log.error(f"Cannot create IDGroup {gid} for paper {paper_number}: {err}")
            raise ValueError(f"Failed to create idgroup for paper {paper_number}")

        gid = "{}d".format(str(paper_number).zfill(4))
        dnmgroup_obj = DNMGroup(
            paper=paper_obj,
            gid=gid,
            expected_number_pages=len(self.spec["doNotMarkPages"]),
            complete=False,
        )
        try:
            dnmgroup_obj.save()
        except DNMGroup.IntegrityError as err:
            log.error(f"Cannot create DNMGroup {gid} for paper {paper_number}: {err}")
            raise ValueError(f"Failed to create dnmgroup for paper {paper_number}")

        # build its QuestionGroups
        for q_idx, question in self.spec["question"].items():
            q = int(q_idx)
            gid = "{}q{}".format(str(paper_number).zfill(4), q)
            v = qv_mapping[q]
            qgroup_obj = QuestionGroup(
                paper=paper_obj,
                gid=gid,
                question=q,
                version=v,
                expected_number_pages=len(question["pages"]),
                max_mark=question["mark"],
                label=question["label"],
            )
            try:
                qgroup_obj.save()
            except QuestionGroup.IntegrityError as err:
                log.error(
                    f"Cannot create QGroup {gid} for paper {paper_number} question {q} version {v}: {err}"
                )
                raise ValueError(
                    f"Failed to create qgroup {gid} for paper {paper_number:04}"
                )

    def add_all_papers_in_qv_map(self, qv_map):
        """Build all the papers given by the qv-map

        qv_map (dict): For each paper give the question-version map.
            Of the form {paper_number: {q: v}}

        returns (pair): If all papers added to DB without errors then
            return (True, []) else return (False, list of errors) where
            the list of errors is a list of pairs (paper_number, error)
        """

        errors = []
        for paper_number, qv_mapping in qv_map.items():
            try:
                self.create_paper_with_qvmapping(paper_number, qv_mapping)
            except ValueError as err:
                errors.append((paper_number, err))
        if errors:
            return False, errors
        else:
            return True, []

    @transaction.atomic
    def remove_all_papers_from_db(self):
        # hopefully we don't actually need to call this outside of testing.
        Paper.objects.filter().delete()

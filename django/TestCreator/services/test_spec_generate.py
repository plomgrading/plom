from ..services import TestSpecService


class TestSpecGenerateService:
    """Methods for generating the final test specification"""

    def __init__(self, spec_service: TestSpecService):
        self.spec = spec_service

    def generate_spec_dict(self):
        """
        Create a dictionary that can be dumped into a .toml file
        """
        spec_dict = {}
        spec = self.spec.specification()

        spec_dict["name"] = self.spec.get_short_name()
        spec_dict["longName"] = self.spec.get_long_name()

        spec_dict["numberOfPages"] = len(spec.pages)
        spec_dict["numberOfVersions"] = self.spec.get_n_versions()
        spec_dict["totalMarks"] = self.spec.get_total_marks()

        spec_dict["numberOfQuestions"] = self.spec.get_n_questions()
        spec_dict["numberToProduce"] = self.spec.get_n_to_produce()

        spec_dict["idPage"] = self.spec.get_id_page_number()
        spec_dict["doNotMarkPages"] = self.spec.get_dnm_page_numbers()

        # notice that plom wants a spec with "question"(singular) not "questions" (plural)
        question = []
        for i in range(self.spec.get_n_questions()):
            q_dict = {}
            q_service = self.spec.questions[i + 1]
            q_dict["pages"] = self.spec.get_question_pages(i + 1)
            q_dict["mark"] = q_service.get_question_marks()
            q_dict["label"] = q_service.get_question_label()
            q_dict["select"] = q_service.get_question_fix_or_shuffle()
            question.append(q_dict)

        spec_dict["question"] = question

        return spec_dict

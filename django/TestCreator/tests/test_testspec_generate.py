from django.test import TestCase
from ..services import TestSpecService, TestSpecGenerateService
from .. import models


class TestSpecGenerateTests(TestCase):
    """Test the code for generating toml input"""

    def test_generate_spec_dict(self):
        """Test services.generate_spec_dict"""
        spec = TestSpecService()
        the_spec = spec.specification()
        the_spec.long_name = 'long'
        the_spec.short_name = 'short'

        the_spec.n_versions = 2
        the_spec.n_to_produce = 2
        the_spec.n_questions = 2
        the_spec.total_marks = 2

        the_spec.pages = {
            "0": {
                'id_page': True,
                'dnm_page': False,
                'question_page': False,
                'thumbnail': 'dummy1.png'
            },
            "1": {
                'id_page': False,
                'dnm_page': True,
                'question_page': False,
                'thumbnail': 'dummy2.png'
            },
            "2": {
                'id_page': False,
                'dnm_page': False,
                'question_page': 1,
                'thumbnail': 'dummy3.png'
            },
            "3": {
                'id_page': False,
                'dnm_page': False,
                'question_page': 2,
                'thumbnail': 'dummy4.png'
            }
        }

        the_spec.save()

        spec.add_question(1, 'Q1', 1, True)
        spec.add_question(2, 'Q2', 1, False)

        gen = TestSpecGenerateService(spec)
        spec_dict = gen.generate_spec_dict()

        self.assertEqual(spec_dict['name'], 'short')
        self.assertEqual(spec_dict['longName'], 'long')

        self.assertEqual(spec_dict['numberOfPages'], 4)
        self.assertEqual(spec_dict['numberOfVersions'], 2)
        self.assertEqual(spec_dict['totalMarks'], 2)
        self.assertEqual(spec_dict['numberOfQuestions'], 2)
        self.assertEqual(spec_dict['numberToProduce'], 2)

        self.assertEqual(spec_dict['idPage'], 1)
        self.assertEqual(spec_dict['doNotMarkPages'], [2])
        self.assertEqual(spec_dict['question'], [
            {
                'pages': [3],
                'mark': 1,
                'label': 'Q1',
                'select': 'shuffle'
            },
            {
                'pages': [4],
                'mark': 1,
                'label': 'Q2',
                'select': 'fix'
            }
        ])

from django.test import TestCase
from .. import services
from .. import models


class TestSpecGenerateTests(TestCase):
    """Test the code for generating toml input"""

    def test_generate_spec_dict(self):
        """Test services.generate_spec_dict"""
        spec = services.load_spec()
        spec.long_name = 'long'
        spec.short_name = 'short'

        spec.n_versions = 2
        spec.n_to_produce = 2
        spec.n_questions = 2
        spec.total_marks = 2

        spec.pages = {
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

        spec.save()

        q1 = models.TestSpecQuestion(index=1, label='Q1', mark=1, shuffle=True)
        q1.save()
        q2 = models.TestSpecQuestion(index=2, label='Q2', mark=1, shuffle=False)
        q2.save()

        spec_dict = services.generate_spec_dict()

        self.assertEqual(spec_dict['name'], 'short')
        self.assertEqual(spec_dict['longName'], 'long')

        self.assertEqual(spec_dict['numberOfPages'], 4)
        self.assertEqual(spec_dict['numberOfVersions'], 2)
        self.assertEqual(spec_dict['totalMarks'], 2)
        self.assertEqual(spec_dict['numberOfQuestions'], 2)
        self.assertEqual(spec_dict['numberToProduce'], 2)

        self.assertEqual(spec_dict['idPage'], 1)
        self.assertEqual(spec_dict['doNotMarkPages'], [2])
        self.assertEqual(spec_dict['questions'], [
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

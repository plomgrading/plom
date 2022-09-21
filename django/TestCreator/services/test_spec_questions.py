from django.core.exceptions import ObjectDoesNotExist
from .. import models
from ..services import TestSpecService


class TestSpecQuestionService:
    """Keep track of a question in a test specification"""

    def __init__(self, one_index: int, spec_service: TestSpecService):
        self.spec = spec_service
        self.one_index = one_index

    def create_question(self, label: str, mark: int, shuffle: bool):
        """Create a question object

        Args:
            label: question label
            mark: max marks for the question
            shuffle: Randomize question across test versions?
        """
        question = models.TestSpecQuestion(
            index=self.one_index, label=label, mark=mark, shuffle=shuffle
        )
        question.save()
        return question

    def remove_question(self):
        """Remove a question from the database, clear any selected pages in TestSpecInfo"""
        question_exists = models.TestSpecQuestion.objects.filter(index=self.one_index)
        if question_exists:
            question = models.TestSpecQuestion.objects.get(index=self.one_index)
            question.delete()

        # remove question data from pages
        test_spec = self.spec.specification()
        pages = test_spec.pages
        for idx, page in pages.items():
            if page["question_page"] == self.one_index:
                page["question_page"] = False
        test_spec.save()

    def get_question(self):
        """Get a question from the database

        Returns:
            models.TestSpecQuestion or None: the question object
        """
        if self.question_exists():
            return models.TestSpecQuestion.objects.get(index=self.one_index)
        else:
            return None

    def question_exists(self):
        """Check if a question exists in the database

        Returns:
            bool: True if it exists, otherwise false
        """
        try:
            question = models.TestSpecQuestion.objects.get(index=self.one_index)
            return True
        except ObjectDoesNotExist:
            return False

    def create_or_replace_question(self, label: str, mark: int, shuffle: bool):
        """Create question in the database. If a question with the same index exists, overwrite it

        Args:
            label: question label
            mark: max marks for the question
            shuffle: Randomize question across test versions?

        Returns:
            models.TestSpecQuestion: question object
        """
        if self.question_exists():
            self.remove_question()

        return self.create_question(label, mark, shuffle)

    def get_question_label(self):
        """Get the question label

        Returns:
            str: question label
        """
        question = self.get_question()
        if question:
            return question.label

    def get_question_marks(self):
        """Get the number of marks for the question

        Returns:
            int: question max mark
        """
        question = self.get_question()
        if question:
            return question.mark

    def get_question_shuffle(self):
        """Get the fix or shuffle status

        Returns:
            Bool: True if shuffle, False if fix
        """
        question = self.get_question()
        return question.shuffle

    def get_question_fix_or_shuffle(self):
        """Get the fix or shuffle status (as a string)

        Returns:
            str: 'shuffle' or 'fix'
        """
        question = self.get_question()
        if question:
            return "shuffle" if question.shuffle else "fix"

    def is_question_completed(self):
        """Are all the necessary fields completed for the question?

        Returns:
            bool: are all the fields truthy?
        """
        return (
            self.get_question_label()
            and self.get_question_marks()
            and self.get_question_shuffle() is not None
        )

    def get_marks_assigned_to_other_questions(self):
        """Get the total marks - current marks (passed down from question detail view)

        Returns:
            int: marks assigned to other questions
        """
        total_marks = self.spec.get_total_assigned_marks()
        if self.get_question_marks():
            other_total = total_marks - self.get_question_marks()
            return other_total
        else:
            return total_marks

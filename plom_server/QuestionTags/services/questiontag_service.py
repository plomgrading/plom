from typing import Any, Dict, List
from django.db.models import QuerySet
from QuestionTags.models import Question

class QuestionService:
    """Class to encapsulate functions for fetching questions."""

    def get_all_questions(self) -> QuerySet[Question]:
        """Get all questions.

        Returns:
            A queryset of questions.
        """
        return Question.objects.all()

    def get_question_count(self) -> int:
        """Get the count of all questions.

        Returns:
            The count of questions.
        """
        return Question.objects.count()

    def get_questions_with_details(self) -> List[Dict[str, Any]]:
        """Get all questions with their details.

        Returns:
            A list of dictionaries with question details.
        """
        questions = self.get_all_questions()
        return [{"id": question.id, "name": question.name} for question in questions]

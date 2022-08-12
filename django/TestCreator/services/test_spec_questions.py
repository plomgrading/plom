from django.core.exceptions import ObjectDoesNotExist
from .. import models
from ..services import TestSpecService


class TestSpecQuestionService:
    """Keep track of a question in a test specification"""
    def __init__(self, one_index: int, spec_service: TestSpecService):
        self.spec = spec_service
        self.one_index = one_index

    def create_question(self, label: str, mark: int, shuffle: bool):
        """ Create a question object
        
        Args:
            label: question label
            mark: max marks for the question
            shuffle: Randomize question across test versions?
        """
        question = models.TestSpecQuestion(index=self.one_index, label=label, mark=mark, shuffle=shuffle)
        question.save()
        return question

    def remove_question(self):
        """ Remove a question from the database, clear any selected pages in TestSpecInfo        
        """
        question_exists = models.TestSpecQuestion.objects.filter(index=self.one_index)
        if question_exists:
            question = models.TestSpecQuestion.objects.get(index=self.one_index)
            question.delete()

        # remove question data from pages
        test_spec = self.spec.specification()
        pages = test_spec.pages
        for idx, page in pages.items():
            if page['question_page'] == self.one_index:
                page['question_page'] = False
        test_spec.save()

    def get_question(self):
        """ Get a question from the database

        Returns:
            models.TestSpecQuestion or None: the question object
        """
        if self.question_exists():
            return models.TestSpecQuestion.objects.get(index=self.one_index)
        else:
            return None

    def question_exists(self):
        """ Check if a question exists in the database

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
        """Get the fix or shufle status (as a string)

        Returns:
            str: 'shuffle' or 'fix'
        """
        question = self.get_question()
        return 'shuffle' if question.shuffle else 'fix'

    def is_question_completed(self):
        """Are all the necessary fields completed for the question?

        Returns:
            bool: are all the fields truthy?
        """
        return self.get_question_label() and self.get_question_marks() and self.get_question_shuffle() != None

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


# """
# Service functions for models.TestSpecQuestion
# """

# def create_question(index: int, label: str, mark: int, shuffle: bool):
#     """ Create a question object
    
#     Args:
#         index: question number (1-indexed!)
#         label: question label
#         mark: max marks for the question
#         shuffle: Randomize question across test versions?
#     """
#     question = models.TestSpecQuestion(index=index, label=label, mark=mark, shuffle=shuffle)
#     question.save()
#     return question


# def remove_question(index: int):
#     """ Remove a question from the database, clear any selected pages in TestSpecInfo
    
#     Args:
#         index: question number (1-indexed!)
#     """
#     question_exists = models.TestSpecQuestion.objects.filter(index=index)
#     if question_exists:
#         question = models.TestSpecQuestion.objects.get(index=index)
#         question.delete()

#     # remove question data from pages
#     test_spec = services.load_spec()
#     pages = test_spec.pages
#     for idx, page in pages.items():
#         if page['question_page'] and page['question_page'] == index:
#             page['question_page'] = False
#     test_spec.save()


# def get_question(index: int):
#     """ Get a question from the database
    
#     Args:
#         index: question number (1-indexed!)

#     Returns:
#         models.TestSpecQuestion or None: the question object
#     """
#     if question_exists(index):
#         return models.TestSpecQuestion.objects.get(index=index)
#     else:
#         return None


# def question_exists(index: int):
#     """ Check if a question exists in the database
    
#     Args:
#         index: question number (1-indexed!)

#     Returns:
#         bool: True if it exists, otherwise false
#     """
#     try:
#         question = models.TestSpecQuestion.objects.get(index=index)
#         return True
#     except ObjectDoesNotExist:
#         return False


# def create_or_replace_question(index: int, label: str, mark: int, shuffle: bool):
#     """Create question in the database. If a question with the same index exists, overwrite it
    
#     Args:
#         index: question number (1-indexed!)
#         label: question label
#         mark: max marks for the question
#         shuffle: Randomize question across test versions?

#     Returns:
#         models.TestSpecQuestion: question object
#     """
#     if question_exists(index):
#         remove_question(index)

#     return create_question(index, label, mark, shuffle)


# def clear_questions():
#     """Remove all the questions"""
#     for i in range(services.get_num_questions()):
#         remove_question(i+1)
#     services.set_num_questions(0)


# def fix_all_questions():
#     """Set all questions to fix (when the user sets the number of test versions to 1)"""
#     for i in range(services.get_num_questions()):
#         q = get_question(i+1)
#         q.shuffle = 'F'


# def get_question_label(index: int):
#     """Get the question label
    
#     Args:
#         index: question number (1-indexed!)

#     Returns:
#         str: question label
#     """
#     question = get_question(index)
#     if question:
#         return question.label


# def get_question_marks(index: int):
#     """Get the number of marks for the question
    
#     Args:
#         index: question number (1-indexed!)

#     Returns:
#         int: question max mark
#     """
#     question = get_question(index)
#     if question:
#         return question.mark


# def get_question_shuffle(index: int):
#     """Get the fix or shuffle status
    
#     Args:
#         index: question number (1-indexed!)

#     Returns:
#         Bool: True if shuffle, False if fix
#     """
#     question = get_question(index)
#     return question.shuffle


# def get_question_fix_or_shuffle(index: int):
#     """Get the fix or shufle status (as a string)
    
#     Args:
#         index: question number (1-indexed!)

#     Returns:
#         str: 'shuffle' or 'fix'
#     """
#     question = get_question(index)
#     return 'shuffle' if question.shuffle else 'fix'


# def is_question_completed(index: int):
#     """Are all the necessary fields completed for the question?
    
#     Args:
#         index: question number (1-indexed!)

#     Returns:
#         bool: are all the fields truthy?
#     """
#     return get_question_label(index) and get_question_marks(index) and get_question_shuffle(index) != None


# def get_total_assigned_marks():
#     """How many marks have been assigned to questions so far?
    
#     Returns:
#         int: marks assigned so far
#     """
#     list_of_marks = models.TestSpecQuestion.objects.all().values_list('mark', flat=True)
#     total_so_far = sum(list_of_marks)
#     return total_so_far


# def get_marks_assigned_to_other_questions(current_marks: int):
#     """Get the total marks - current marks (passed down from question detail view)

#     Args:
#         current_marks: number of marks assigned to this question previously

#     Returns:
#         int: marks assigned to other questions
#     """
#     total_marks = get_total_assigned_marks()
#     if current_marks:
#         other_total = total_marks - current_marks
#         return other_total
#     else:
#         return total_marks


# def get_available_marks(current_marks=0):
#     """Given the already filled out questions, how many marks left are there?

#     Args:
#         current_marks (int): How many marks were previously assigned to this question?
    
#     Returns:
#         int: total marks for test - total marks assigned so far
#     """
#     total_marks = services.get_total_marks()
#     marks_left = total_marks - get_total_assigned_marks() + current_marks
#     if 0 > marks_left:
#         raise RuntimeError("You've assigned more marks to questions than in the total_marks field")
#     return marks_left

from .. import models
from ..services import TestSpecService
from ..services import ReferencePDFService


class TestSpecProgressService:
    """Keep track of which parts of the test specification wizard have been completed"""
    def __init__(self, spec_service: TestSpecService):
        self.spec = spec_service

    def is_names_completed(self):
        """Return True if the first page of the wizard has been completed"""
        has_long_name = False
        has_short_name = False
        has_n_versions = False

        if self.spec.get_long_name() != '':
            has_long_name = True

        if self.spec.get_short_name() != '':
            has_short_name = True

        if self.spec.get_n_versions() > 0:
            has_n_versions = True

        return has_short_name and has_long_name and has_n_versions

    def is_pdf_page_completed(self):
        """Return True if the second page of the wizard has been completed"""
        ref_service = ReferencePDFService(self.spec)

        try:
            pdf = ref_service.get_pdf()
            has_reference_pdf = True
        except RuntimeError:
            has_reference_pdf = False

        return has_reference_pdf

    def is_id_page_completed(self):
        """Return True if the third page of the wizard has been completed"""
        id_page = self.spec.get_id_page_number()
        return not id_page == None

    def is_question_page_completed(self):
        """Return True if the fourth page of the wizard has been completed"""
        n_questions = self.spec.get_n_questions()
        total_marks = self.spec.get_total_marks()
        return n_questions > 0 and total_marks > 0

    def is_question_detail_page_completed(self, index):
        """Return True if a given question detail page has been completed"""
        if index not in self.spec.questions:
            return False

        question = self.spec.questions[index]
        return question.is_question_completed()

    def are_all_questions_completed(self):
        """Return True if all the question detail pages have been completed"""
        n_questions = self.spec.get_n_questions()
        for i in range(n_questions):
            if not self.is_question_detail_page_completed(i):
                return False
        return True

    def is_dnm_page_completed(self):
        """Return True if the do-not-mark page has been submitted"""
        return self.spec.specification().dnm_page_submitted

    def is_validate_page_completed(self):
        """placeholder"""
        the_spec = self.spec.specification()
        return the_spec.validate_page_sumbitted

    def get_progress_dict(self):
        """Return a dictionary with completion data for the wizard."""
        progress_dict = {}
        progress_dict['names'] = self.is_names_completed()
        progress_dict['upload'] = self.is_pdf_page_completed()
        progress_dict['id_page'] = self.is_id_page_completed()
        progress_dict['questions_page'] = self.is_question_page_completed()
        progress_dict['question_list'] = [self.is_question_detail_page_completed(i+1) for i in range(self.spec.get_n_questions())]
        progress_dict['dnm_page'] = self.is_dnm_page_completed()
        progress_dict['validate'] = self.is_validate_page_completed()

        return progress_dict

    def is_everything_complete(self):
        """Return false if any item in the progress dict is false - otherwise, every part of the wizard is complete, so return true"""
        progress_dict = self.get_progress_dict()

        for key, value in progress_dict.items():
            if key == 'question_list':
                for q in value:
                    if not q:
                        return False
            elif not value:
                return False

        return True

    def progress_is_anything_complete(self):
        """Return true if any of the wizard pages are completed, false otherwise"""
        progress_dict = self.get_progress_dict()
        vals = progress_dict.values()
        return (True in vals)


# """
# Service functions for models.TestsSpecProgress
# """

# def get_progress():
#     """
#     Get or init the singleton test progress object

#     Returns:
#         models.TestSpecProgress
#     """
#     progress, created = models.TestSpecProgress.objects.get_or_create(pk=1)
#     return progress


# def reset_progress():
#     """
#     Clear the progress object

#     Returns:
#         models.TestSpecProgress
#     """
#     models.TestSpecProgress.objects.all().delete()
#     return get_progress()


# def progress_init_questions():
#     """
#     Create a dict of each question in the test: is question i's detail page submitted?
#     """
#     question_dict = {i: False for i in range(services.get_num_questions())}
#     progress = get_progress()
#     progress.are_questions_completed = question_dict
#     progress.save()


# def progress_clear_questions():
#     """Reset the questions progress dict"""
#     progress = get_progress()

#     progress.are_questions_completed = {}
#     progress.save()
    

# def progress_set_names(complete: bool):
#     """Set the completed status of the names page"""
#     progress = get_progress()
#     progress.is_names_completed = complete
#     progress.save()


# def progress_set_versions_pdf(complete: bool):
#     """Set the completed status of the versions/upload pdf page"""
#     progress = get_progress()
#     progress.is_versions_pdf_completed = complete
#     progress.save()


# def progress_set_id_page(complete: bool):
#     """Set the completed status of the ID select page"""
#     progress = get_progress()
#     progress.is_id_page_completed = complete
#     progress.save()


# def progress_set_question_page(complete: bool):
#     """Set the completed status of the names page"""
#     progress = get_progress()
#     progress.is_question_page_completed = complete
#     progress.save()


# def progress_set_question_detail_page(index: int, complete: bool):
#     """Set the completed status of a question detail page"""
#     progress = get_progress()
#     progress.are_questions_completed[index] = complete
#     progress.save()


# def progress_set_dnm_page(complete: bool):
#     """Set the completed status of the Do-not-mark selection page"""
#     progress = get_progress()
#     progress.is_dnm_page_completed = complete
#     progress.save()


# def progress_set_validate_page(complete: bool):
#     """Set the completed status of the validation page"""
#     progress = get_progress()
#     progress.is_validate_page_completed = complete
#     progress.save()


# def get_progress_dict():
#     """Return a dictionary with completion data for the wizard."""
#     progress = get_progress()

#     progress_dict = {}
#     progress_dict['names'] = progress.is_names_completed
#     progress_dict['upload'] = progress.is_versions_pdf_completed
#     progress_dict['id_page'] = progress.is_id_page_completed
#     progress_dict['questions_page'] = progress.is_question_page_completed
#     progress_dict['question_list'] = get_question_progress_for_template()
#     progress_dict['dnm_page'] = progress.is_dnm_page_completed
#     progress_dict['validate'] = progress.is_validate_page_completed

#     return progress_dict


# def get_question_progress_for_template():
#     """Converts the TestSpecProgress questions JSON into a list of bools. For ease in rendering the sidebar.
#     """
#     progress = get_progress()
#     questions = progress.are_questions_completed
#     questions_list = []

#     n_questions = len(questions.keys())
#     for i in range(n_questions):
#         val = questions[str(i)]
#         questions_list.append(val)

#     return questions_list


# def progress_is_everything_complete():
#     """Return false if any item in the progress dict is false - otherwise, every part of the wizard is complete, so return true"""
#     progress_dict = get_progress_dict()

#     for key, value in progress_dict.items():
#         if key == 'question_list':
#             for q in value:
#                 if not q:
#                     return False
#         elif not value:
#             return False

#     return True


# def progress_is_anything_complete():
#     """Return true if any of the wizard pages are completed, false otherwise"""
#     progress_dict = get_progress_dict()
#     vals = progress_dict.values()
#     return (True in vals)

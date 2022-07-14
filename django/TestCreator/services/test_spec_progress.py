from .. import models
from . import *

"""
Service functions for models.TestsSpecProgress
"""

def get_progress():
    """
    Get or init the singleton test progress object

    Returns:
        models.TestSpecProgress
    """
    progress, created = models.TestSpecProgress.objects.get_or_create(pk=1)
    return progress


def reset_progress():
    """
    Clear the progress object

    Returns:
        models.TestSpecProgress
    """
    models.TestSpecProgress.objects.all().delete()
    return get_progress()


def progress_init_questions():
    """
    Create a dict of each question in the test: is question i's detail page submitted?
    """
    question_dict = {i: False for i in range(get_num_questions())}
    progress = get_progress()
    progress.are_questions_completed = question_dict
    progress.save()


def progress_clear_questions():
    """Reset the questions progress dict"""
    progress = get_progress()
    progress.are_questions_completed = {}
    progress.save()


def progress_clear_pages():
    """Reset the pages progress dict"""
    progress = get_progress()
    progress.are_pages_selected = {}
    progress.save()
    

def progress_init_pages():
    """
    Create a dict of each page in the test: has page i been selected by something?
    """
    num_pages = len(load_spec().pages)
    page_dict = {i: False for i in range(num_pages)}
    progress = get_progress()
    progress.are_pages_selected = page_dict
    progress.save()


def progress_set_names(complete: bool):
    """Set the completed status of the names page"""
    progress = get_progress()
    progress.is_names_completed = complete
    progress.save()


def progress_set_versions_pdf(complete: bool):
    """Set the completed status of the versions/upload pdf page"""
    progress = get_progress()
    progress.is_versions_pdf_completed = complete
    progress.save()


def progress_set_id_page(complete: bool):
    """Set the completed status of the ID select page"""
    progress = get_progress()
    progress.is_id_page_completed = complete
    progress.save()


def progress_set_question_page(complete: bool):
    """Set the completed status of the names page"""
    progress = get_progress()
    progress.is_question_page_completed = complete
    progress.save()


def progress_set_question_detail_page(index: int, complete: bool):
    """Set the completed status of a question detail page"""
    progress = get_progress()
    progress.are_questions_completed[index] = complete
    progress.save()


def progress_set_page_selected(index: int, selected: bool):
    """Set the selected status of a test page"""
    progress = get_progress()
    progress.are_pages_selected[index] = selected
    progress.save()


def progress_set_dnm_page(complete: bool):
    """Set the completed status of the Do-not-mark selection page"""
    progress = get_progress()
    progress.is_dnm_page_completed = complete
    progress.save()


def get_progress_dict():
    """Return a dictionary with completion data for the wizard."""
    progress = get_progress()

    progress_dict = {}
    progress_dict['names'] = progress.is_names_completed
    progress_dict['upload'] = progress.is_versions_pdf_completed
    progress_dict['id_page'] = progress.is_id_page_completed
    progress_dict['questions_page'] = progress.is_question_page_completed
    progress_dict['question_list'] = get_question_progress_for_template()
    progress_dict['dnm_page'] = progress.is_dnm_page_completed
    progress_dict['selected'] = progress.are_pages_selected

    return progress_dict


def get_question_progress_for_template():
    """Converts the TestSpecProgress questions JSON into a list of bools. For ease in rendering the sidebar.
    """
    progress = get_progress()
    questions = progress.are_questions_completed
    questions_list = []

    n_questions = len(questions.keys())
    for i in range(n_questions):
        val = questions[str(i)]
        questions_list.append(val)

    return questions_list

import pathlib
import json
from .. import models

"""
Service functions for models.TestSpecInfo
"""

def load_spec():
    """Get the singelton TestSpecInfo object from the database 

    Returns:
        TestSpecInfo: the TestSpec object
    """
    spec, created = models.TestSpecInfo.objects.get_or_create(pk=1)
    return spec


def reset_spec():
    """Clear the TestSpecInfo object

    Returns:
        TestSpecInfo: the newly cleared TestSpec object
    """
    models.TestSpecInfo.objects.all().delete()
    return load_spec()


def get_long_name():
    """Return the TestSpecInfo long_name field

    Returns:
        str: the test's long name
    """
    return load_spec().long_name


def set_long_name(long_name: str):
    """Set the test's long name
    
    Args:
        long_name: the new long name
    """
    test_spec = load_spec()
    test_spec.long_name = long_name
    test_spec.save()


def get_short_name():
    """Return the TestSpecInfo short_name field

    Returns:
        str: the test's short name
    """
    return load_spec().short_name


def get_num_versions():
    """Get the number of test versions
    
    Returns:
        int: versions
    """
    return load_spec().n_versions


def set_num_versions(n_versions: int):
    """Set the number of test versions
    
    Args:
        n_versions: number of versions
    """
    test_spec = load_spec()
    test_spec.n_versions = n_versions
    test_spec.save()


def get_num_to_produce():
    """Get the number of test papers to produce
    
    Returns:
        int: number to produce
    """
    return load_spec().n_to_produce


def set_num_to_produce(num: int):
    """Set the number of test papers to produce
    
    Args:
        num: number of test papers
    """
    test_spec = load_spec()
    test_spec.n_to_produce = num
    test_spec.save()


def set_short_name(short_name: str):
    """Set the short name of the test
    
    Args:
        short_name: the short name
    """
    test_spec = load_spec()
    test_spec.short_name = short_name
    test_spec.save()


def get_num_questions():
    """Get the number of questions
    
    Returns:
        int: number of questions in the test
    """
    return load_spec().n_questions


def set_num_questions(num: int):
    """Set the number of questions in the test

    Args:
        num: the number of questions
    """
    test_spec = load_spec()
    test_spec.n_questions = num
    test_spec.save()


def get_total_marks():
    """Get the total number of marks in the teest
    
    Returns:
        int: total marks
    """
    return load_spec().total_marks


def set_total_marks(total: int):
    """Set the total number of marks in the test

    Args:
        total: full number of marks
    
    """
    test_spec = load_spec()
    test_spec.total_marks = total
    test_spec.save()


def set_pages(pdf: models.ReferencePDF):
    """
    Initialize page dictionary

    Args:
        pdf: the ReferencePDF object
    """
    test_spec = load_spec()

    thumbnail_folder = pathlib.Path('thumbnails') / pdf.filename_slug

    for i in range(pdf.num_pages):
        thumbnail_path = thumbnail_folder / f'{pdf.filename_slug}-thumbnail{i}.png'
        test_spec.pages[i] = {
            'id_page': False,
            'dnm_page': False,
            'question_page': False,
            'thumbnail': str(thumbnail_path)
        }
    test_spec.save()


def get_page_list():
    """
    Convert page dict into a list of dicts for looping over in a template

    Returns:
        list: List of page dictionaries in order
    """
    test_spec = load_spec()
    return [test_spec.pages[str(i)] for i in range(len(test_spec.pages))]


def get_pages_for_id_select_page():
    """
    Return a list of pages, with an extra field representing the @click statement to pass to alpine
    For the ID page

    Returns:
        list: page dictionaries
    """
    page_list = get_page_list()
    for i in range(len(page_list)):
        page = page_list[i]
        if not page['dnm_page'] and not page['question_page']:
            page['at_click'] = f'page{i}selected = !page{i}selected'
        else:
            page['at_click'] = ''
    return page_list


def get_pages_for_question_detail_page(quetion_id: int):
    """
    Return a list of pages, with an extra field representing the @click statement to pass to alpine
    For the question detail page

    Args:
        question_id: The index of the question page
    
    Returns:
        list: page dictionaries
    """
    page_list = get_page_list()
    for i in range(len(page_list)):
        page = page_list[i]
        if page['question_page'] and page['question_page'] == quetion_id:
            page['at_click'] = f'page{i}selected = !page{i}selected'
        elif page['question_page']:
            page['at_click'] = ''
        elif page['dnm_page'] or page['id_page']:
            page['at_click'] = ''
        else:
            page['at_click'] = f'page{i}selected = !page{i}selected'
    return page_list


def get_pages_for_dnm_select_page():
    """
    Return a list of pages, with an extra field representing the @click statement to pass to alpine
    For the do-not-mark page

    Returns:
        list: page dictionaries
    """
    page_list = get_page_list()
    for i in range(len(page_list)):
        page = page_list[i]
        if not page['id_page'] and not page['question_page']:
            page['at_click'] = f'page{i}selected = !page{i}selected'
        else:
            page['at_click'] = ''
    return page_list


def set_id_page(page_idx: int):
    """
    Set a page as the test's only ID page

    Args:
        page_idx: the index of the ID page
    """
    test_spec = load_spec()
    str_idx = str(page_idx)
    for idx, value in test_spec.pages.items():
        if idx == str_idx:
            test_spec.pages[idx]['id_page'] = True
        else:
            test_spec.pages[idx]['id_page'] = False
    test_spec.save()


def clear_id_page():
    """
    Remove the ID page from the test
    """
    test_spec = load_spec()
    for idx, value in test_spec.pages.items():
        test_spec.pages[idx]['id_page'] = False
    test_spec.save()


def get_id_page_number():
    """
    Get the 1-indexed page number of the ID page

    Returns:
        int or None: ID page index
    """
    pages = load_spec().pages
    for idx, page in pages.items():
        if page['id_page']:
            return int(idx) + 1

    return None


def set_do_not_mark_pages(pages: list):
    """
    Set these pages as the test's do-not-mark pages

    Args:
        page: list of ints - 0-indexed page numbers
    """
    test_spec = load_spec()
    str_ids = [str(i) for i in pages]
    for idx, page in test_spec.pages.items():
        if idx in str_ids:
            test_spec.pages[idx]['dnm_page'] = True
        else:
            test_spec.pages[idx]['dnm_page'] = False
    test_spec.save()


def get_dnm_page_numbers():
    """
    Return a list of one-indexed page numbers for do-not-mark pages

    Returns:
        list: 0-indexed page numbers
    """
    dnm_pages = []
    pages = load_spec().pages
    for idx, page in pages.items():
        if page['dnm_page']:
            dnm_pages.append(int(idx) + 1)
    return dnm_pages


def set_question_pages(pages: list, question: int):
    """
    Set these pages as the test's pages for question i

    Args:
        pages: 0-indexed list of page numbers
        question: question id
    """
    test_spec = load_spec()
    str_ids = [str(i) for i in pages]
    for idx, page in test_spec.pages.items():
        if idx in str_ids:
            test_spec.pages[idx]['question_page'] = question
        elif test_spec.pages[idx]['question_page'] == question:
            test_spec.pages[idx]['question_page'] = False

    test_spec.save()


def get_question_pages(question_id: int):
    """
    Returns a 1-indexed list of page numbers for a question

    Args:
        question_id: index of the question

    Returns:
        list: 0-indexed page numbers
    """
    question_pages = []
    pages = load_spec().pages
    for idx, page in pages.items():
        if page['question_page'] and page['question_page'] == question_id:
            question_pages.append(int(idx) + 1)
    return question_pages


def get_id_page_alpine_xdata():
    """
    Generate top-level x-data object for the ID page template

    Returns:
        str: JSON object dump
    """
    pages = get_page_list()
    
    x_data = {}
    for i in range(len(pages)):
        page = pages[i]
        if page['id_page']:
            x_data[f'page{i}selected'] = True
        else:
            x_data[f'page{i}selected'] = False

    return json.dumps(x_data)


def get_question_detail_page_alpine_xdata(question_id: int):
    """
    Generate top-level x-data object for the question detail page template

    Args:
        question_id: question index

    Returns:
        str: JSON object dump
    """
    pages = get_page_list()

    x_data = {}
    for i in range(len(pages)):
        page = pages[i]
        if page['question_page'] and page['question_page'] == question_id:
            x_data[f'page{i}selected'] = True
        else:
            x_data[f'page{i}selected'] = False

    return json.dumps(x_data)


def get_dnm_page_alpine_xdata():
    """
    Generate top-level x-data object for the do not mark page template

    Returns:
        str: JSON object dump
    """
    pages = get_page_list()

    x_data = {}
    for i in range(len(pages)):
        page = pages[i]
        if page['dnm_page']:
            x_data[f'page{i}selected'] = True
        else:
            x_data[f'page{i}selected'] = False

    return json.dumps(x_data)
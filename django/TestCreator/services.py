import pathlib
import fitz
import json
from django.utils.text import slugify
from django.core.exceptions import ObjectDoesNotExist
from . import models

"""
TODO: refactor by splitting into subject?
By read-only and read/write?
"""


"""
Test spec functions
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


"""
Question functions
"""

def create_question(index: int, label: str, mark: int, shuffle: bool):
    """ Create a question object
    
    Args:
        index: question number (1-indexed!)
        label: question label
        mark: max marks for the question
        shuffle: Randomize question across test versions?
    """
    question = models.TestSpecQuestion(index=index, label=label, mark=mark, shuffle=shuffle)
    question.save()
    return question


def remove_question(index: int):
    """ Remove a question from the database, clear any selected pages in TestSpecInfo
    
    Args:
        index: question number (1-indexed!)
    """
    question_exists = models.TestSpecQuestion.objects.filter(index=index)
    if question_exists:
        question = models.TestSpecQuestion.objects.get(index=index)
        question.delete()

    # remove question data from pages
    test_spec = load_spec()
    pages = test_spec.pages
    for idx, page in pages.items():
        if page['question_page'] and page['question_page'] == index:
            page['question_page'] = False
    test_spec.save()


def get_question(index: int):
    """ Get a question from the database
    
    Args:
        index: question number (1-indexed!)

    Returns:
        models.TestSpecQuestion or None: the question object
    """
    if question_exists(index):
        return models.TestSpecQuestion.objects.get(index=index)
    else:
        return None


def question_exists(index: int):
    """ Check if a question exists in the database
    
    Args:
        index: question number (1-indexed!)

    Returns:
        bool: True if it exists, otherwise false
    """
    try:
        question = models.TestSpecQuestion.objects.get(index=index)
        return True
    except ObjectDoesNotExist:
        return False


def create_or_replace_question(index: int, label: str, mark: int, shuffle: bool):
    """Create question in the database. If a question with the same index exists, overwrite it
    
    Args:
        index: question number (1-indexed!)
        label: question label
        mark: max marks for the question
        shuffle: Randomize question across test versions?

    Returns:
        models.TestSpecQuestion: question object
    """
    if question_exists(index):
        remove_question(index)

    return create_question(index, label, mark, shuffle)


def clear_questions():
    """Remove all the questions"""
    for i in range(get_num_questions()):
        remove_question(i+1)
    set_num_questions(0)


def fix_all_questions():
    """Set all questions to fix (when the user sets the number of test versions to 1)"""
    for i in range(get_num_questions()):
        q = get_question(i+1)
        q.shuffle = 'F'


def get_question_label(index: int):
    """Get the question label
    
    Args:
        index: question number (1-indexed!)

    Returns:
        str: question label
    """
    question = get_question(index)
    if question:
        return question.label


def get_question_marks(index: int):
    """Get the number of marks for the question
    
    Args:
        index: question number (1-indexed!)

    Returns:
        int: question max mark
    """
    question = get_question(index)
    if question:
        return question.mark


def get_question_fix_or_shuffle(index: int):
    """Get the fix or shuffle status
    
    Args:
        index: question number (1-indexed!)

    Returns:
        str: 'Shuffle' or 'Fix'
    """
    question = get_question(index)
    if question:
        if question.shuffle == 'S':
            return 'Shuffle'
        else:
            return 'Fix'


def is_question_completed(index: int):
    """Are all the necessary fields completed for the question?
    
    Args:
        index: question number (1-indexed!)

    Returns:
        bool: are all the fields truthy?
    """
    return get_question_label(index) and get_question_marks(index) and get_question_fix_or_shuffle(index)


"""
PDF functions
"""

def create_pdf(slug: str, pages: int, pdf) -> models.ReferencePDF:
    """
    Create a PDF in the database and save the file on disk

    Args:
        slug: url-safe filename (w/o extension)
        pages: number of pages in the pdf
        pdf: in-memory PDF file

    Returns:
        models.ReferencePDF: the reference PDF object
    """
    pdf = models.ReferencePDF(filename_slug=slug, num_pages=pages, pdf=pdf)
    pdf.save()
    return pdf


def delete_pdf():
    """
    Clear the ReferencePDF table
    """
    pdfs = models.ReferencePDF.objects.all()
    pdfs.delete()


def get_and_save_pdf_images(pdf: models.ReferencePDF) -> None:
    """
    Get raster image of each PDF page, and save them to disk for displaying

    Args:
        pdf: ReferencePDF object
    """
    slug = pdf.filename_slug
    pathname = pathlib.Path('TestCreator') / 'media' / f'{slug}.pdf'
    # TODO: use pathlib
    if pathname.exists():
        pdf_doc = fitz.Document(pathname)

        thumbnail_dir = pathlib.Path('TestCreator') / 'static' / 'thumbnails' / slug
        if not thumbnail_dir.exists():
            thumbnail_dir.mkdir()

        for i in range(pdf_doc.page_count):
            page_pixmap = pdf_doc[i].get_pixmap()
            save_path = thumbnail_dir / f'{slug}-thumbnail{i}.png'
            page_pixmap.save(save_path)

    else:
        raise RuntimeError(f'Document at {pathname} does not exist.')


def create_page_thumbnail_list(pdf: models.ReferencePDF):
    """
    Create list of image paths to send to frontend for pdf thumbnail rendering

    Args:
        pdf: ReferencePDF object

    Returns:
        list: page thumbnail paths
    """

    pages = []
    thumbnail_folder = pathlib.Path('thumbnails') / pdf.filename_slug
    for i in range(pdf.num_pages):
        thumbnail = thumbnail_folder / f'{pdf.filename_slug}-thumbnail{i}.png'
        pages.append(thumbnail)

    return pages


"""
Test progress functions
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

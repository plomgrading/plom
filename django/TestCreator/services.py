import os
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
    spec, created = models.TestSpecInfo.objects.get_or_create(pk=1)
    return spec


def reset_spec():
    models.TestSpecInfo.objects.all().delete()
    return load_spec()


def get_long_name():
    return load_spec().long_name


def set_long_name(long_name: str):
    test_spec = load_spec()
    test_spec.long_name = long_name
    test_spec.save()


def get_short_name():
    return load_spec().short_name


def set_short_name(short_name: str):
    test_spec = load_spec()
    test_spec.short_name = short_name
    test_spec.save()


def get_num_questions():
    return load_spec().n_questions


def set_num_questions(num: int):
    test_spec = load_spec()
    test_spec.n_questions = num
    test_spec.save()


def get_total_marks():
    return load_spec().total_marks


def set_total_marks(total: int):
    test_spec = load_spec()
    test_spec.total_marks = total
    test_spec.save()


def set_pages(pdf: models.ReferencePDF):
    """
    Initialize page dictionary
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
    """
    test_spec = load_spec()
    return [test_spec.pages[str(i)] for i in range(len(test_spec.pages))]


def get_pages_for_id_select_page():
    """
    Return a list of pages, with an extra field representing the @click statement to pass to alpine
    For the ID page
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
    """
    pages = load_spec().pages
    for idx, page in pages.items():
        if page['id_page']:
            return int(idx) + 1

    return None


def set_do_not_mark_pages(pages: list):
    """
    Set these pages as the test's do-not-mark pages
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
    question = models.TestSpecQuestion(index=index, label=label, mark=mark, shuffle=shuffle)
    question.save()
    return question


def remove_question(index: int):
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
    if question_exists(index):
        return models.TestSpecQuestion.objects.get(index=index)
    else:
        return None


def question_exists(index: int):
    try:
        question = models.TestSpecQuestion.objects.get(index=index)
        return True
    except ObjectDoesNotExist:
        return False


def create_or_replace_question(index: int, label: str, mark: int, shuffle: bool):
    if question_exists(index):
        remove_question(index)

    return create_question(index, label, mark, shuffle)


def clear_questions():
    for i in range(get_num_questions()):
        remove_question(i+1)


def get_question_label(index: int):
    question = get_question(index)
    if question:
        return question.label


def get_question_marks(index: int):
    question = get_question(index)
    if question:
        return question.mark


def get_question_fix_or_shuffle(index: int):
    question = get_question(index)
    if question:
        if question.shuffle == 'S':
            return 'Shuffle'
        else:
            return 'Fix'


"""
PDF functions
"""

def create_pdf(slug: str, pages: int, pdf) -> models.ReferencePDF:
    """
    Create a PDF in the database and save the file on disk
    """
    pdf = models.ReferencePDF(filename_slug=slug, num_pages=pages, pdf=pdf)
    pdf.save()
    return pdf


def get_and_save_pdf_images(pdf: models.ReferencePDF) -> None:
    """
    Get raster image of each PDF page, and save them to disk for displaying
    """
    slug = pdf.filename_slug
    pathname = pathlib.Path('TestCreator') / 'media' / f'{slug}.pdf'
    # TODO: use pathlib
    if pathname.exists():
        pdf_doc = fitz.Document(pathname)

        thumbnail_dir = pathlib.Path('TestCreator') / 'static' / 'thumbnails' / slug
        if not thumbnail_dir.exists():
            os.mkdir(thumbnail_dir)

        for i in range(pdf_doc.page_count):
            page_pixmap = pdf_doc[i].get_pixmap()
            save_path = thumbnail_dir / f'{slug}-thumbnail{i}.png'
            page_pixmap.save(save_path)

    else:
        raise RuntimeError(f'Document at {pathname} does not exist.')


def create_page_thumbnail_list(pdf: models.ReferencePDF) -> None:
    """
    Create list of image paths to send to frontend for pdf thumbnail rendering
    """

    pages = []
    thumbnail_folder = pathlib.Path('thumbnails') / pdf.filename_slug
    for i in range(pdf.num_pages):
        thumbnail = thumbnail_folder / f'{pdf.filename_slug}-thumbnail{i}.png'
        pages.append(thumbnail)

    return pages

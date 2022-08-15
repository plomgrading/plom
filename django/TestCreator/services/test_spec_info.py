import pathlib
import json
import fitz
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from .. import models
from .. import services


class TestSpecService:
    """Keep track of changes to the test specification."""

    def __init__(self):
        self.questions = {}
        for i in range(1, self.get_n_questions()+1):
            self.questions[i] = services.TestSpecQuestionService(i, self)

    def specification(self):
        """Get the latest form of the TestSpecInfo instance

        Returns:
            TestSpecInfo: the singleton TestSpec object
        """
        spec, created = models.TestSpecInfo.objects.get_or_create(pk=1)
        return spec

    def reset_specification(self):
        """Clear the TestSpecInfo object

        Returns:
            TestSpecInfo: the newly cleared TestSpec object
        """
        models.TestSpecInfo.objects.all().delete()
        return self.specification()

    def get_long_name(self):
        """Return the TestSpecInfo long_name field

        Returns:
            str: the test's long name
        """
        return self.specification().long_name

    def set_long_name(self, long_name: str):
        """Set the test's long name
        
        Args:
            long_name: the new long name
        """
        test_spec = self.specification()
        test_spec.long_name = long_name
        test_spec.save()

    def get_short_name(self):
        """Return the TestSpecInfo short_name field

        Returns:
            str: the test's short name
        """
        return self.specification().short_name

    def set_short_name(self, short_name: str):
        """Set the short name of the test
        
        Args:
            short_name: the short name
        """
        test_spec = self.specification()
        test_spec.short_name = short_name
        test_spec.save()

    def get_n_versions(self):
        """Get the number of test versions
        
        Returns:
            int: versions
        """
        return self.specification().n_versions

    def set_n_versions(self, n: int):
        """Set the number of test versions
        
        Args:
            n number of versions
        """
        test_spec = self.specification()
        test_spec.n_versions = n
        test_spec.save()

    def get_n_to_produce(self):
        """Get the number of test papers to produce
        
        Returns:
            int: number to produce
        """
        return self.specification().n_to_produce

    def set_n_to_produce(self, n: int):
        """Set the number of test papers to produce
        
        Args:
            n: number of test papers
        """
        test_spec = self.specification()
        test_spec.n_to_produce = n
        test_spec.save()

    def get_n_questions(self):
        """Get the number of questions
        
        Returns:
            int: number of questions in the test
        """
        return self.specification().n_questions

    def set_n_questions(self, n: int):
        """Set the number of questions in the test

        Args:
            n: the number of questions
        """
        test_spec = self.specification()
        test_spec.n_questions = n
        test_spec.save()

    def has_question(self, index):
        """Return True if there is a TestSpecQuestionService object for a question with the given index"""
        return self.questions[index].get_question() != None

    def add_question(self, index: int, label: str, mark: int, shuffle: bool):
        """Add or replace a TestSpecQuestion instance
        
        Args:
            index: one-index of the question
            label: question label
            mark: max marks
            shuffle: 'shuffle'? if not, 'fix'
        """
        self.questions[index] = services.TestSpecQuestionService(index, self)
        self.questions[index].create_or_replace_question(label, mark, shuffle)

    def clear_questions(self):
        """Remove all questions"""
        for i in range(1, self.get_n_questions()+1):
            if i in self.questions:
                self.questions[i].remove_question()
                del self.questions[i]

    def fix_all_questions(self):
        """Set all questions to 'fix'"""
        for i in range(self.get_n_questions()):
            q = self.questions[i+1].get_question()
            q.shuffle = False
            q.save()

    def get_available_marks(self, index: int):
        """Given the already filled out questions, how many marks left are there?

        Args:
            index: index of current question
        
        Returns:
            int: total marks for test - total marks assigned so far
        """
        total_marks = self.get_total_marks()
        question_service = self.questions[index]
        available = total_marks - question_service.get_marks_assigned_to_other_questions()
        return available

    def get_total_marks(self):
        """Get the total number of marks in the teest
        
        Returns:
            int: total marks
        """
        return self.specification().total_marks

    def set_total_marks(self, total: int):
        """Set the total number of marks in the test

        Args:
            total: full number of marks
        
        """
        test_spec = self.specification()
        test_spec.total_marks = total
        test_spec.save()

    
    def get_total_assigned_marks(self):
        """How many marks have been assigned to questions so far?
        
        Returns:
            int: marks assigned so far
        """
        list_of_marks = models.TestSpecQuestion.objects.all().values_list('mark', flat=True)
        total_so_far = sum(list_of_marks)
        return total_so_far

    def set_pages(self, pdf: models.ReferencePDF):
        """
        Initialize page dictionary

        Args:
            pdf: the ReferencePDF object
        """
        test_spec = self.specification()

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

    def get_n_pages(self):
        """
        Get the number of pages set in the spec

        Returns:
            int: The number of pages
        """
        return len(self.specification().pages)

        
    def get_page_list(self):
        """
        Convert page dict into a list of dicts for looping over in a template

        Returns:
            list: List of page dictionaries in order
        """
        test_spec = self.specification()
        return [test_spec.pages[str(i)] for i in range(len(test_spec.pages))]

    def set_id_page(self, page_idx: int):
        """
        Set a page as the test's only ID page

        Args:
            page_idx: the index of the ID page
        """
        test_spec = self.specification()
        str_idx = str(page_idx)
        for idx, value in test_spec.pages.items():
            if idx == str_idx:
                test_spec.pages[idx]['id_page'] = True
            else:
                test_spec.pages[idx]['id_page'] = False
        test_spec.save()

    def clear_id_page(self):
        """
        Remove the ID page from the test
        """
        test_spec = self.specification()
        for idx, value in test_spec.pages.items():
            test_spec.pages[idx]['id_page'] = False
        test_spec.save()

    def get_id_page_number(self):
        """
        Get the 1-indexed page number of the ID page

        Returns:
            int or None: ID page index
        """
        pages = self.specification().pages
        for idx, page in pages.items():
            if page['id_page']:
                return int(idx) + 1

        return None

    def set_do_not_mark_pages(self, pages: list):
        """
        Set these pages as the test's do-not-mark pages

        Args:
            page: list of ints - 0-indexed page numbers
        """
        test_spec = self.specification()
        str_ids = [str(i) for i in pages]
        for idx, page in test_spec.pages.items():
            if idx in str_ids:
                test_spec.pages[idx]['dnm_page'] = True
            else:
                test_spec.pages[idx]['dnm_page'] = False
        test_spec.save()

    def get_dnm_page_numbers(self):
        """
        Return a list of one-indexed page numbers for do-not-mark pages

        Returns:
            list: 0-indexed page numbers
        """
        dnm_pages = []
        pages = self.specification().pages
        for idx, page in pages.items():
            if page['dnm_page']:
                dnm_pages.append(int(idx) + 1)
        return dnm_pages

    def set_question_pages(self, pages: list, question: int):
        """
        Set these pages as the test's pages for question i

        Args:
            pages: 0-indexed list of page numbers
            question: question id
        """
        test_spec = self.specification()
        str_ids = [str(i) for i in pages]
        for idx, page in test_spec.pages.items():
            if idx in str_ids:
                test_spec.pages[idx]['question_page'] = question
            elif test_spec.pages[idx]['question_page'] == question:
                test_spec.pages[idx]['question_page'] = False

        test_spec.save()

    def get_question_pages(self, question_id: int):
        """
        Returns a 1-indexed list of page numbers for a question

        Args:
            question_id: index of the question

        Returns:
            list: 0-indexed page numbers
        """
        question_pages = []
        pages = self.specification().pages
        for idx, page in pages.items():
            if page['question_page'] == question_id:
                question_pages.append(int(idx)+1)
        return question_pages

    def is_there_some_spec_data(self):
        """Returns true if at least one page is completed"""
        prog = services.TestSpecProgressService(self)
        return prog.is_anything_complete()

    def read_spec_dict(self, input_spec, pdf_path):
        """Load a test specification from a dictionary. Assumes for now that the dictionary is valid and complete.
        
        It wants a toml-esque input dictionary:
        {
            'name': str,
            'longName': str,
            'numberOfPages': int,
            'numberOfVersions': int,
            'totalMarks': int,
            'numberOfQuestions': int,
            'numberToProduce': int,
            'idPage': int,
            'doNotMarkPages': list(int),
            'questions': list(dict) {
                'pages: list(int),
                'mark': int,
                'label': str,
                'select': str, "fix" or "shuffle",
            },
        }

        And a sample PDF file.
        """

        # names page
        self.set_short_name(input_spec['name'])
        self.set_long_name(input_spec['longName'])
        self.set_n_versions(input_spec['numberOfVersions'])

        # PDF page
        pdf_path = pathlib.Path(pdf_path)
        pdf_doc = pdf_path.open('rb').read()
        pdf_service = services.ReferencePDFService(self)

        # validate that file is a PDF
        pdf = fitz.open(stream=pdf_doc)
        if 'PDF' not in pdf.metadata['format']:
            raise ValidationError('File is not a valid PDF.')

        n_pages = input_spec['numberOfPages']
        pdf_service.new_pdf(slugify(pdf_path.stem), n_pages, SimpleUploadedFile(pdf_path.name, pdf_doc))

        # ID page
        self.set_id_page(input_spec['idPage'] - 1)

        # Questions and total marks
        self.set_n_questions(input_spec['numberOfQuestions'])
        self.set_n_to_produce(input_spec['numberToProduce'])
        self.set_total_marks(input_spec['totalMarks'])

        # question details
        for i in range(self.get_n_questions()):
            question = input_spec['questions'][i]
            q_pages = [j-1 for j in question['pages']]
            label = question['label']
            mark = question['mark']
            shuffle = question['select'] == 'shuffle'

            self.add_question(i+1, label, mark, shuffle)
            self.set_question_pages(q_pages, i+1)

        # do-not-mark pages
        dnm_pages = [j-1 for j in input_spec['doNotMarkPages']]
        self.set_do_not_mark_pages(dnm_pages)
        the_spec = self.specification()
        the_spec.dnm_page_submitted = True
        
        # validate (assume valid for now)
        the_spec.validate_page_submitted = True
        the_spec.save()

    def get_pages_for_id_select_page(self):
        """
        Return a list of pages, with an extra field representing the @click statement to pass to alpine
        For the ID page

        Returns:
            list: page dictionaries
        """
        page_list = self.get_page_list()
        for i in range(len(page_list)):
            page = page_list[i]
            if not page['dnm_page'] and not page['question_page']:
                page['at_click'] = f'page{i}selected = !page{i}selected'
            else:
                page['at_click'] = ''
        return page_list

    def get_pages_for_question_detail_page(self, quetion_id: int):
        """
        Return a list of pages, with an extra field representing the @click statement to pass to alpine
        For the question detail page

        Args:
            question_id: The index of the question page
        
        Returns:
            list: page dictionaries
        """
        page_list = self.get_page_list()
        for i in range(len(page_list)):
            page = page_list[i]
            if page['question_page'] == quetion_id:
                page['at_click'] = f'page{i}selected = !page{i}selected'
            elif page['question_page']:
                page['at_click'] = ''
            elif page['dnm_page'] or page['id_page']:
                page['at_click'] = ''
            else:
                page['at_click'] = f'page{i}selected = !page{i}selected'
        return page_list

    def get_pages_for_dnm_select_page(self):
        """
        Return a list of pages, with an extra field representing the @click statement to pass to alpine
        For the do-not-mark page

        Returns:
            list: page dictionaries
        """
        page_list = self.get_page_list()
        for i in range(len(page_list)):
            page = page_list[i]
            if not page['id_page'] and not page['question_page']:
                page['at_click'] = f'page{i}selected = !page{i}selected'
            else:
                page['at_click'] = ''
        return page_list

    def get_id_page_alpine_xdata(self):
        """
        Generate top-level x-data object for the ID page template

        Returns:
            str: JSON object dump
        """
        pages = self.get_page_list()
        
        x_data = {}
        for i in range(len(pages)):
            page = pages[i]
            if page['id_page']:
                x_data[f'page{i}selected'] = True
            else:
                x_data[f'page{i}selected'] = False

        return json.dumps(x_data)

    def get_question_detail_page_alpine_xdata(self, question_id: int):
        """
        Generate top-level x-data object for the question detail page template

        Args:
            question_id: question index

        Returns:
            str: JSON object dump
        """
        pages = self.get_page_list()

        x_data = {}
        for i in range(len(pages)):
            page = pages[i]
            if page['question_page'] == question_id:
                x_data[f'page{i}selected'] = True
            else:
                x_data[f'page{i}selected'] = False

        return json.dumps(x_data)

    def get_dnm_page_alpine_xdata(self):
        """
        Generate top-level x-data object for the do not mark page template

        Returns:
            str: JSON object dump
        """
        pages = self.get_page_list()

        x_data = {}
        for i in range(len(pages)):
            page = pages[i]
            if page['dnm_page']:
                x_data[f'page{i}selected'] = True
            else:
                x_data[f'page{i}selected'] = False

        return json.dumps(x_data)

    def validate_specification(self):
        """
        Validate the current state of the test specification, using a TestSpecProgress service
        """
        prog = services.TestSpecProgressService(self)
        progress_dict = prog.get_progress_dict()

        errors_to_raise = []
        
        if not progress_dict['names']:
            errors_to_raise.append('Test needs a long name, short name, and number of versions.')

        if not progress_dict['upload']:
            errors_to_raise.append('Test needs a reference PDF.')

        if not progress_dict['id_page']:
            errors_to_raise.append('Test needs an ID page.')

        if not progress_dict['questions_page']:
            errors_to_raise.append('Test needs questions.')

        questions = progress_dict['question_list']
        for i in range(len(questions)):
            if not questions[i]:
                errors_to_raise.append(f'Question {i+1} is incomplete.')

        pages = self.get_page_list()
        for i in range(len(pages)):
            cur_page = pages[i]
            if not cur_page['id_page'] and not cur_page['dnm_page'] and not cur_page['question_page']:
                errors_to_raise.append(f'Page {i+1} has not been assigned. Did you mean to make it a do-not-mark page?')

        marks_for_all_questions = self.get_total_assigned_marks()
        if marks_for_all_questions != self.get_total_marks():
            errors_to_raise.append(f'There are {self.get_total_marks()} marks assigned to the test, but {marks_for_all_questions} marks in total assigned to the questions. You can change the total marks on the \"Questions\" page, or the marks for a single question on its individual page.')

        if errors_to_raise:
            raise ValidationError(errors_to_raise)

        the_spec = self.specification()
        the_spec.validate_page_submitted = True
        the_spec.save()

    def is_specification_valid(self):
        """Validates specification, and return a boolean instead of raising ValidationErrors"""
        try:
            self.validate_specification()
            return True
        except ValidationError:
            return False

    def unvalidate(self):
        """If something about the test is changed, un-submit the validation page"""
        the_spec = self.specification()
        the_spec.validate_page_sumbitted = False
        the_spec.save()

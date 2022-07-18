from . import *

def generate_spec_dict():
    """
    Create a dictionary that can be dumped into a .toml file
    """
    spec_dict = {}
    spec = load_spec()

    spec_dict['name'] = get_short_name()
    spec_dict['longName'] = get_long_name()

    spec_dict['numberOfPages'] = len(spec.pages)
    spec_dict['numberOfVersions'] = get_num_versions()
    spec_dict['totalMarks'] = get_total_marks()

    spec_dict['numberOfQuestions'] = get_num_questions()
    spec_dict['numberToProduce'] = get_num_to_produce()

    spec_dict['idPage'] = get_id_page_number()
    spec_dict['doNotMarkPages'] = get_dnm_page_numbers()

    questions = []
    for i in range(get_num_questions()):
        q_dict = {}
        q_dict['pages'] = get_question_pages(i+1)
        q_dict['mark'] = get_question_marks(i+1)
        q_dict['label'] = get_question_label(i+1)
        q_dict['select'] = get_question_fix_or_shuffle(i+1).lower()
        questions.append(q_dict)

    spec_dict['questions'] = questions

    return spec_dict
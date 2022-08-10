from .. import services

def generate_spec_dict():
    """
    Create a dictionary that can be dumped into a .toml file
    """
    spec_dict = {}
    spec = services.load_spec()

    spec_dict['name'] = services.get_short_name()
    spec_dict['longName'] = services.get_long_name()

    spec_dict['numberOfPages'] = len(spec.pages)
    spec_dict['numberOfVersions'] = services.get_num_versions()
    spec_dict['totalMarks'] = services.get_total_marks()

    spec_dict['numberOfQuestions'] = services.get_num_questions()
    spec_dict['numberToProduce'] = services.get_num_to_produce()

    spec_dict['idPage'] = services.get_id_page_number()
    spec_dict['doNotMarkPages'] = services.get_dnm_page_numbers()

    questions = []
    for i in range(services.get_num_questions()):
        q_dict = {}
        q_dict['pages'] = services.get_question_pages(i+1)
        q_dict['mark'] = services.get_question_marks(i+1)
        q_dict['label'] = services.get_question_label(i+1)
        q_dict['select'] = services.get_question_fix_or_shuffle(i+1).lower()
        questions.append(q_dict)

    spec_dict['questions'] = questions

    return spec_dict
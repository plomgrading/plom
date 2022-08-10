# TODO - get rid of this file and replace these functions by proper services.


def is_there_a_valid_spec():
    return True


def how_many_test_pages():
    return 6


def how_many_test_versions():
    return 3


def how_many_test_versions_uploaded():
    return 1


def list_of_uploaded_test_sources():
    return [{"version": 1}, {"version": 2}, {"version": 3}]


# functions to govern which steps are available to the user


def are_all_source_tests_uploaded():
    return how_many_test_versions() == how_many_test_versions_uploaded()


def can_I_upload_source_tests():
    return is_there_a_valid_spec()


def can_I_prename():
    return is_there_a_valid_spec()


def can_I_qvmap():
    return is_there_a_valid_spec()


def get_demo_spec():
    return {
        "name": "plomdemo",
        "longName": "Midterm Demo using Plom",
        "numberOfVersions": 2,
        "numberOfPages": 6,
        "totalMarks": 20,
        "numberOfQuestions": 3,
        "idPage": 1,
        "doNotMarkPages": [2],
        "question": {
            "1": {"pages": [3], "mark": 5, "select": "shuffle"},
            "2": {"label": "Q(2)", "pages": [4], "mark": 5, "select": "fix"},
            "3": {"label": "Ex.3", "pages": [5, 6], "mark": 10, "select": "shuffle"},
        },
    }

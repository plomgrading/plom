# TODO - get rid of this file and replace these functions by proper services.


def is_there_a_valid_spec():
    return True


def how_many_test_pages():
    return 6


def how_many_test_versions():
    return 3


def how_many_test_versions_uploaded():
    return 1


# functions to govern which steps are available to the user


def are_all_source_tests_uploaded():
    return how_many_test_versions() == how_many_test_versions_uploaded()


def can_I_upload_source_tests():
    return is_there_a_valid_spec()


def can_I_prename():
    return is_there_a_valid_spec()


def can_I_qvmap():
    return is_there_a_valid_spec()

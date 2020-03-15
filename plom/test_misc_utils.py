from .misc_utils import format_int_list_with_runs


def test_runs():
    L = ["1", "2", "3", "4", "7", "10", "11", "12", "13", "14", "64"]
    uout = "1–4, 7, 10–14, 64"
    aout = "1-4, 7, 10-14, 64"
    assert format_int_list_with_runs(L, use_unicode=True) == uout
    assert format_int_list_with_runs(L, use_unicode=False) == aout
    assert format_int_list_with_runs(L) in (aout, uout)


def test_shortruns():
    L = ["1", "2", "4", "5", "6", "7", "9", "10", "12", "78", "79", "80"]
    out = "1, 2, 4-7, 9, 10, 12, 78-80"
    assert format_int_list_with_runs(L, use_unicode=False) == out

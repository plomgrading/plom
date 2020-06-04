from .utils import my_hash


def test_hash():
    assert my_hash("12345678", salt="salt") == "351525727036"
    assert my_hash("12345678", salt="salty") == "782385405730"
    assert my_hash("12345679", salt="salt") == "909470548567"
    assert 1 == 0
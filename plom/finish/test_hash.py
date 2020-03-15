from .utils import myhash

def test_hash():
    assert myhash("12345678", salt="salt") == "351525727036"
    assert myhash("12345678", salt="salty") == "782385405730"
    assert myhash("12345679", salt="salt") == "909470548567"

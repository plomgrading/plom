# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path

from pytest import raises
import fitz

from plom.finish.coverPageBuilder import makeCover


def test_cover_page(tmpdir):
    f = Path(tmpdir) / "foo.pdf"
    data = [[1, 1, 3, 4], [2, 1, 4, 6], [3, 2, 0, 5]]
    makeCover(data, f, test_num="0123", info=("Agnesi", 12345678))
    doc = fitz.open(f)
    assert len(doc) == 1
    pg = doc[0]
    text = pg.get_text()
    assert "Agnesi" in text
    assert "Test number: 0123" in text
    assert "12345678" in text


def test_cover_page_hardcoded_letter_paper(tmpdir):
    f = Path(tmpdir) / "foo.pdf"
    data = [[1, 1, 4], [2, 1, 6]]
    makeCover(data, f, solution=True)
    doc = fitz.open(f)
    pg = doc[0]
    assert pg.rect.width == 612
    assert pg.rect.height == 792


def test_cover_page_solution(tmpdir):
    f = "soln.pdf"
    data = [[1, 1, 4], [2, 1, 6]]
    makeCover(data, f, solution=True)
    doc = fitz.open(f)
    assert len(doc) == 1
    pg = doc[0]
    text = pg.get_text()
    assert "Results" not in text
    assert "Solutions" in text


def test_cover_page_question_labels(tmpdir):
    f = Path(tmpdir) / "foo.pdf"
    data = [["Q1", 1, 3, 4], ["Ex2", 1, 4, 6], ["Exercise 3", 2, 0, 5]]
    makeCover(data, f)
    doc = fitz.open(f)
    pg = doc[0]
    text = pg.get_text()
    assert "Q1" in text
    assert "Ex2" in text
    assert "Exercise 3" in text


def test_cover_page_non_ascii(tmpdir):
    f = Path(tmpdir) / "foo.pdf"
    data = [["№1", 1, 3, 4], ["Q二", 1, 4, 6]]
    makeCover(data, f, test_num="0123", info=("我爱你", 12345678))
    doc = fitz.open(f)
    pg = doc[0]
    text = pg.get_text()
    assert "№1" in text
    assert "Q二" in text
    assert "我爱你" in text


def test_cover_page_at_least_20_questions_one_page_issue2519(tmpdir):
    f = Path(tmpdir) / "foo.pdf"
    N = 20
    data = [[n, 1, 2, 3] for n in range(1, N + 1)]
    makeCover(data, f, test_num="0123", info=("A", 12345678))
    doc = fitz.open(f)
    assert len(doc) == 1

    data = [[n, 1, 3] for n in range(1, N + 1)]
    makeCover(data, f, test_num="0123", info=("A", 12345678), solution=True)
    doc = fitz.open(f)
    assert len(doc) == 1


def test_cover_page_a_great_many_questions_multipage_issue2519(tmpdir):
    tmpdir = Path(tmpdir)
    N = 100
    data = [[f"Q{n}", 1, 2, 3] for n in range(1, N + 1)]
    f = tmpdir / "foo.pdf"
    makeCover(data, f)
    doc = fitz.open(f)
    assert len(doc) >= 3

    data = [[f"Q{n}", 1, 3] for n in range(1, N + 1)]
    f = tmpdir / "soln.pdf"
    makeCover(data, f, solution=True)
    doc = fitz.open(f)
    assert len(doc) >= 3


def test_cover_page_totalling(tmpdir):
    # a bit of a messy test, but I want to check a few sums
    check = (
        (3, 4, [[1, 1, 3, 4]]),
        (10, 25, [[1, 1, 4, 4], [2, 1, 5, 6], [3, 2, 1, 15]]),
        (9, 25, [[1, 1, 4, 4], [2, 1, 5, 6], [3, 2, 0, 15]]),
        (5.2, 9.4, [[1, 1, 1, 2], [2, 1, 4.2, 7.4]]),
    )
    for score, total, data in check:
        f = Path(tmpdir) / "foo.pdf"
        makeCover(data, f, footer=False)
        doc = fitz.open(f)
        pg = doc[0]
        stuff = pg.get_text("words")
        # sort by y position
        stuff.sort(key=lambda x: x[3])
        last_four = stuff[-4:]
        for x in last_four:
            print(x)
        words = [x[4] for x in last_four]
        assert "total" in words
        assert str(score) in words
        assert str(total) in words
        doc.close()


def test_cover_page_doesnt_like_negatives(tmpdir):
    # a bit of a messy test, but I want to check a few sums
    check = ((10, 25, [[1, 1, 4, -3], [2, 1.2, 5, 6]]),)
    for score, total, data in check:
        f = Path(tmpdir) / "foo.pdf"
        with raises(AssertionError):
            makeCover(data, f)


def test_cover_page_foolish_stuff_gives_errors(tmpdir):
    # a bit of a messy test, but I want to check a few sums
    check = (
        (10, 25, [[1, 1, 4, "four"], [2, 1, 5, 6]]),
        (9, 25, [[1, 1, 4, 4], [2, 1, "five", 6]]),
        (42, 42, [[1, 1, None, 2], [2, 1, 2, 4]]),
        (42, 42, [[1, 1, 0, None], [2, 1, 2, 4]]),
    )
    for score, total, data in check:
        f = Path(tmpdir) / "foo.pdf"
        with raises(AssertionError):
            makeCover(data, f)


def test_cover_page_title(tmpdir):
    f = Path(tmpdir) / "foo.pdf"
    s = "Math 947 Differential Sub-manifolds Quiz 7"
    data = [[1, 1, 3, 4], [2, 1, 4, 6]]
    makeCover(data, f, exam_name=s, test_num="0123", info=("A", 12345678))
    doc = fitz.open(f)
    pg = doc[0]
    text = pg.get_text()
    assert s in text

    data = [[1, 1, 4], [2, 1, 6]]
    makeCover(data, f, exam_name=s, solution=True)
    doc = fitz.open(f)
    pg = doc[0]
    text = pg.get_text()
    assert s in text

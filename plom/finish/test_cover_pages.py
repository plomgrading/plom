# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Colin B. Macdonald

from pytest import raises

import fitz

from plom.finish.coverPageBuilder import makeCover


def test_cover_page(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    data = [["Q1", 1, 3, 4], ["Q2", 1, 4, 6], ["Q3", 2, 0, 5]]
    makeCover(data, f, test_num=1234, info=("Agnesi", "12345678"))
    with fitz.open(f) as doc:
        assert len(doc) == 1
        pg = doc[0]
        text = pg.get_text()
        assert "Agnesi" in text
        assert "Test number: 1234" in text
        assert "12345678" in text


def test_cover_page_test_num_leading_zero_pad(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    data = [["Q1", 1, 3, 4], ["Q2", 1, 4, 6], ["Q3", 2, 0, 5]]
    makeCover(data, f, test_num=12, info=("Agnesi", "12345678"))
    with fitz.open(f) as doc:
        assert "Test number: 0012" in doc[0].get_text()


def test_cover_page_leading_zero_sid(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    data = [["Q1", 1, 3, 4], ["Q2", 1, 4, 6], ["Q3", 2, 0, 5]]
    makeCover(data, f, test_num=123, info=("Someone", "00123400"))
    with fitz.open(f) as doc:
        assert "00123400" in doc[0].get_text()


def test_cover_page_hardcoded_letter_paper(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    data = [["A", 1, 4], ["B", 1, 6]]
    makeCover(data, f, solution=True)
    with fitz.open(f) as doc:
        pg = doc[0]
        assert pg.rect.width == 612
        assert pg.rect.height == 792


def test_cover_page_solution(tmp_path) -> None:
    f = tmp_path / "soln.pdf"
    data = [["A", 1, 4], ["B", 1, 6]]
    makeCover(data, f, solution=True)
    with fitz.open(f) as doc:
        assert len(doc) == 1
        pg = doc[0]
        text = pg.get_text()
    assert "Results" not in text
    assert "Solutions" in text


def test_cover_page_question_labels(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    data = [["Q1", 1, 3, 4], ["Ex2", 1, 4, 6], ["Exercise 3", 2, 0, 5]]
    makeCover(data, f)
    with fitz.open(f) as doc:
        pg = doc[0]
        text = pg.get_text()
    assert "Q1" in text
    assert "Ex2" in text
    assert "Exercise 3" in text


def test_cover_page_non_ascii(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    data = [["№1", 1, 3, 4], ["Q二", 1, 4, 6]]
    makeCover(data, f, test_num=123, info=("我爱你", "12345678"))
    with fitz.open(f) as doc:
        pg = doc[0]
        text = pg.get_text()
    assert "№1" in text
    assert "Q二" in text
    assert "我爱你" in text


def test_cover_page_at_least_20_questions_one_page_issue2519(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    N = 20
    data = [[f"Q{n}", 1, 2, 3] for n in range(1, N + 1)]
    makeCover(data, f, test_num=123, info=("A", "12345678"))
    with fitz.open(f) as doc:
        assert len(doc) == 1

    data = [[f"Q{n}", 1, 3] for n in range(1, N + 1)]
    makeCover(data, f, test_num=123, info=("A", "12345678"), solution=True)
    with fitz.open(f) as doc:
        assert len(doc) == 1


def test_cover_page_a_great_many_questions_multipage_issue2519(tmp_path) -> None:
    N = 100
    data = [[f"Q{n}", 1, 2, 3] for n in range(1, N + 1)]
    f = tmp_path / "foo.pdf"
    makeCover(data, f)
    with fitz.open(f) as doc:
        assert len(doc) >= 3

    data = [[f"Q{n}", 1, 3] for n in range(1, N + 1)]
    f = tmp_path / "soln.pdf"
    makeCover(data, f, solution=True)
    with fitz.open(f) as doc:
        assert len(doc) >= 3


def test_cover_page_totalling(tmp_path) -> None:
    # a bit of a messy test, but I want to check a few sums
    check = (
        (3, 4, [["Q1", 1, 3, 4]]),
        (10, 25, [["Q1", 1, 4, 4], ["Q2", 1, 5, 6], ["Q3", 2, 1, 15]]),
        (9, 25, [["Q1", 1, 4, 4], ["Q2", 1, 5, 6], ["Q3", 2, 0, 15]]),
        (5.2, 9.4, [["Q1", 1, 1, 2], ["Q2", 1, 4.2, 7.4]]),
    )
    for score, total, data in check:
        f = tmp_path / "foo.pdf"
        makeCover(data, f, footer=False)
        with fitz.open(f) as doc:
            pg = doc[0]
            stuff = pg.get_text("words")
        # sort by y position
        stuff.sort(key=lambda x: x[3])
        last_four = stuff[-4:]
        # for x in last_four:
        #     print(x)
        words = [x[4] for x in last_four]
        assert "total" in words
        assert str(score) in words
        assert str(total) in words


def test_cover_page_label_cannot_be_None(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    data = [[None, 1, 4]]
    with raises(AssertionError, match="string"):
        makeCover(data, f, solution=True)


def test_cover_page_labels_must_be_strings(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    data = [[8675309, 1, 6]]
    with raises(AssertionError, match="string"):
        makeCover(data, f, solution=True)


def test_cover_page_doesnt_like_negatives(tmp_path) -> None:
    check = ((10, 25, [["Q1", 1, 4, -3], ["Q2", 1.2, 5, 6]]),)
    for score, total, data in check:
        f = tmp_path / "foo.pdf"
        with raises(AssertionError, match="non-negative"):
            makeCover(data, f)


def test_cover_page_foolish_stuff_gives_errors(tmp_path) -> None:
    check = (
        (10, 25, [["Q1", 1, 4, "four"], ["Q2", 1, 5, 6]]),
        (9, 25, [["Q1", 1, 4, 4], ["Q2", 1, "five", 6]]),
        (42, 42, [["Q1", 1, None, 2], ["Q2", 1, 2, 4]]),
        (42, 42, [["Q1", 1, 0, None], ["Q2", 1, 2, 4]]),
    )
    for score, total, data in check:
        f = tmp_path / "foo.pdf"
        with raises(AssertionError, match="numeric"):
            makeCover(data, f)


def test_cover_page_title(tmp_path) -> None:
    f = tmp_path / "foo.pdf"
    s = "Math 947 Differential Sub-manifolds Quiz 7"
    data = [["Q1", 1, 3, 4], ["Q2", 1, 4, 6]]
    makeCover(data, f, exam_name=s, test_num=123, info=("A", "12345678"))
    with fitz.open(f) as doc:
        pg = doc[0]
        text = pg.get_text()
    assert s in text

    data = [["Q1", 1, 4], ["Q2", 1, 6]]
    makeCover(data, f, exam_name=s, solution=True)
    with fitz.open(f) as doc:
        pg = doc[0]
        text = pg.get_text()
    assert s in text

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path

import fitz

from plom.finish.coverPageBuilder import makeCover


def test_cover_page(tmpdir):
    f = Path(tmpdir) / "foo.pdf"
    data = [[1, 1, 3, 4], [2, 1, 4, 6], [3, 2, 0, 5]]
    makeCover("0123", "Agnesi", 12345678, data, f)
    doc = fitz.open(f)
    assert len(doc) == 1
    pg = doc[0]
    text = pg.get_text()
    assert "Agnesi" in text
    assert "Test number = 0123" in text
    assert "12345678" in text


def test_cover_page_solution(tmpdir):
    f = Path(tmpdir) / "soln.pdf"
    data = [[1, 1, 4, 4], [2, 1, 1066, 6]]
    makeCover("0123", "A", 12345678, data, f, solution=True)
    doc = fitz.open(f)
    assert len(doc) == 1
    pg = doc[0]
    text = pg.get_text()
    assert "Results" not in text
    assert "Solutions" in text
    assert "1066" not in text


def test_cover_page_question_labels(tmpdir):
    f = Path(tmpdir) / "foo.pdf"
    data = [["Q1", 1, 3, 4], ["Ex2", 1, 4, 6], ["Exercise 3", 2, 0, 5]]
    makeCover("0123", "A", 12345678, data, f)
    doc = fitz.open(f)
    pg = doc[0]
    text = pg.get_text()
    assert "Q1" in text
    assert "Ex2" in text
    assert "Exercise 3" in text


def test_cover_page_non_ascii(tmpdir):
    f = Path(tmpdir) / "foo.pdf"
    data = [["№1", 1, 3, 4], ["Q二", 1, 4, 6]]
    makeCover("0123", "我爱你", 12345678, data, f)
    doc = fitz.open(f)
    pg = doc[0]
    text = pg.get_text()
    assert "№1" in text
    assert "Q二" in text
    assert "我爱你" in text


def test_cover_page_19_questions_one_page(tmpdir):
    # see Issue #2519
    f = Path(tmpdir) / "foo.pdf"
    N = 19
    data = [[n, 1, 2, 3] for n in range(1, N + 1)]
    for tf in (True, False):
        makeCover("0123", "A", 12345678, data, f, solution=tf)
        doc = fitz.open(f)
        assert len(doc) == 1


def test_cover_page_totalling(tmpdir):
    # a bit of a messy test, but I want to check a few sums
    check = (
        (3, 4, [[1, 1, 3, 4]]),
        (10, 25, [[1, 1, 4, 4], [2, 1, 5, 6], [3, 2, 1, 15]]),
        (9, 25, [[1, 1, 4, 4], [2, 1, 5, 6], [3, 2, 0, 15]]),
        (0, 0, []),
    )
    for score, total, data in check:
        f = Path(tmpdir) / "foo.pdf"
        makeCover("0123", "A", 12345678, data, f)
        doc = fitz.open(f)
        pg = doc[0]
        stuff0 = pg.get_text("words")
        stuff = []
        for x in stuff0:
            if x[3] > 700:
                # ignore the footer, rather crude
                # maybe we should have a kwarg to not add that
                continue
            stuff.append(x)
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

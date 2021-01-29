# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

import time
from pathlib import Path
from .comment_list import (
    comments_new_default_list,
    comments_save_list,
    comments_load_from_file,
)


def test_load_default_comments():
    clist = comments_new_default_list()
    assert len(clist) >= 1
    for c in clist:
        assert c["text"]


def test_default_comment_has_at_least_one_latex():
    clist = comments_new_default_list()
    assert any([r"\LaTeX" in c["text"] for c in clist])


def test_default_comments_created_in_past():
    clist = comments_new_default_list()
    now = time.gmtime()
    for c in clist:
        assert now >= c["created"]


def test_save_load_comments(tmpdir):
    tmp_path = Path(tmpdir)
    clist1 = comments_new_default_list()
    comments_save_list(clist1, comment_dir=tmp_path, filename="foo.toml")
    clist2 = comments_load_from_file(tmp_path / "foo.toml")
    clist1.sort(key=lambda C: -len(C["text"]))
    clist2.sort(key=lambda C: -len(C["text"]))
    for c, d in zip(clist1, clist2):
        assert c["text"] == d["text"]
    # TODO: fails b/c of processing dates: post-toml they are just lists...
    # assert clist1 == clist2

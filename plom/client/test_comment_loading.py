# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

import time
from .comment_list import comments_new_default_list


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

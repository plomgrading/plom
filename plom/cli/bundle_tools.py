# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from pathlib import Path
from typing import Any

from plom.cli import with_messenger
from plom.scan.question_list_utils import _parse_questions


@with_messenger
def upload_bundle(pdf: Path, *, msgr) -> dict[str, Any]:
    """Upload a bundle from a local pdf file."""
    return msgr.new_server_upload_bundle(pdf)


@with_messenger
def bundle_map_page(
    bundle_id: int, page: int, *, papernum: int, questions: str | list, msgr
) -> None:
    """Map a page of a bundle to zero or more questions."""
    questions = _parse_questions(questions)
    msgr.new_server_bundle_map_page(
        bundle_id, page, papernum=papernum, questions=questions
    )

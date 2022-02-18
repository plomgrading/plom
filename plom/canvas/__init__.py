# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021-2022 Colin B. Macdonald

"""Plom features supporting integration with Canvas"""

__DEFAULT_CANVAS_API_URL__ = "https://canvas.ubc.ca"

from .canvas_utils import get_student_list, download_classlist
from .canvas_utils import (
    canvas_login,
    get_assignment_by_id_number,
    get_conversion_table,
    get_courses_teaching,
    get_course_by_id_number,
    get_section_by_id_number,
    get_sis_id_to_canvas_id_table,
    interactively_get_assignment,
    interactively_get_course,
    interactively_get_section,
)

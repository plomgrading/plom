# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Vala Vakilian

"""Plom tools for producing papers"""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

paperdir = "papersToPrint"
from .buildNamedPDF import build_all_papers, confirm_processed, identify_prenamed
from .buildClasslist import possible_surname_fields, possible_given_name_fields
from .buildClasslist import process_class_list
from .upload_classlist import upload_classlist
from .upload_classlist import get_messenger
from .buildDatabaseAndPapers import build_database, build_papers

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Aidan Murphy

from csv import DictWriter
from io import StringIO

from plom.cli import with_messenger


@with_messenger
def get_pqvmap_as_csv_string(msgr) -> str:
    """Retrieve the pqvmap from a server, and format it as a .csv string.

    Keyword Args:
        msgr:  An active Messenger object.

    Returns:
        A string containing the pqvmap as a .csv string.
    """
    pqvmap_json = msgr.new_server_get_pqvmap()
    pqvmap_dict_list = []
    for paper_number, version_dict in pqvmap_json.items():
        pqvdict = {"paper_number": paper_number}
        for paper_element, version in version_dict.items():
            if not paper_element == "id":
                paper_element = "q" + paper_element
            pqvdict.update({paper_element: version})

        pqvmap_dict_list.append(pqvdict)

    with StringIO() as stringbuffer:
        writer = DictWriter(stringbuffer, pqvmap_dict_list[0].keys())

        writer.writeheader()
        writer.writerows(pqvmap_dict_list)
        csv_string = stringbuffer.getvalue()

    return csv_string

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

import re


class RenamePDFFile:
    def get_PDF_name(self, file_path: str):
        return re.sub(r"^.*?/papersToPrint/", "", file_path)

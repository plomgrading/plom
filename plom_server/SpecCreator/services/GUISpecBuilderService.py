# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Aidan Murphy

import base64

from plom_server.Preparation.services import SourceService


def get_source_file_images_as_base64_str(version: int) -> list[str]:
    djangofile_list = SourceService.get_reference_images_as_list(version)
    b64_image_list = []
    for abstract_django_file in djangofile_list:
        print(abstract_django_file)
        with abstract_django_file.open("rb") as f:
            f.seek(0)
            image_bytes = f.read()
        b64_bytes = base64.b64encode(image_bytes).decode("ascii")
        b64_image_list.append(b64_bytes)
    return b64_image_list

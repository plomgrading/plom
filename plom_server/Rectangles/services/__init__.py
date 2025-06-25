# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Andrew Rechnitzer
# Copyright (C) 2025 Colin B. Macdonald


from .rectangle import (
    RectangleExtractor,
    get_reference_qr_coords_for_page,
    get_reference_rectangle_for_page,
    extract_rect_region_from_image,
)

from .idbox_utils import (
    get_idbox_rectangle,
    set_idbox_rectangle,
    clear_idbox_rectangle,
)

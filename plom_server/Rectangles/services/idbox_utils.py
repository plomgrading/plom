# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Andrew Rechnitzer

from plom_server.Identify.models import IDRectangle


def set_idbox_rectangle(
    version: int, left: float, top: float, right: float, bottom: float
) -> None:
    """Set the QR-coordinate system idbox coordinates for a particular version."""
    try:
        idr = IDRectangle.objects.get(version=version)
        idr.top = top
        idr.left = left
        idr.bottom = bottom
        idr.right = right
        idr.save()
    except IDRectangle.DoesNotExist:
        IDRectangle.objects.create(
            version=version, left=left, top=top, right=right, bottom=bottom
        )


def get_idbox_rectangle(version: int) -> dict[str, float] | None:
    """Get the QR-coordinate system idbox coordinates for a particular version."""
    try:
        idr = IDRectangle.objects.get(version=version)
        return {
            "top_f": idr.top,
            "left_f": idr.left,
            "bottom_f": idr.bottom,
            "right_f": idr.right,
        }
    except IDRectangle.DoesNotExist:
        return None


def clear_idbox_rectangle(version: int) -> None:
    """Clear the QR-coordinate system idbox coordinates for a particular version."""
    try:
        idr = IDRectangle.objects.get(version=version)
        idr.delete()
    except IDRectangle.DoesNotExist:
        pass

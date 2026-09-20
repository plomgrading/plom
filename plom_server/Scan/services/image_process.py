# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from typing import Any


class PageImageProcessor:
    """Functions for processing a page-image: rotation."""

    @classmethod
    def get_page_orientation(cls, qr_code_data: dict[str, dict[str, Any]]) -> str:
        """Return a string representing a page orientation.

        The choices are:
            upright: page doesn't need to be rotated
            upside_down: page should be rotated 180 degrees
            turned_left: page should be rotated -90 degrees
            turned_right: page should be rotated 90 degrees

        The "expected" quadrants are the "quadrant" values in qr_code_data,
        and are labelled 1-4. The "actual" quadrants are the keys in qr_code_data,
        and are labelled NW, NE, SW, SE:

        upright:
            2---1   NW---NE
            |   |    |   |
            |   |    |   |
            3---4   SW---SE

        turned_right:
            3------2    NW---NE
            |      |     |   |
            4------1     |   |
                        SW---SE

        turned_left:
            1------4    NW---NE
            |      |     |   |
            2------3     |   |
                        SW---SE

        upside_down:
            4---3    NW---NE
            |   |     |   |
            |   |     |   |
            1---2    SW---SE

        Args:
            qr_code_data: data parsed from page-image QR codes.

        Returns:
            str: short description of the orientation.

        Raises:
            RuntimeError: something inconsistent in the QR data.
        """
        northeast_orientation = None
        qr = qr_code_data.get("NE")
        if qr:
            qr_orientation = qr.get("quadrant")
            if qr_orientation is not None:
                northeast_orientation = cls._check_corner(
                    val_from_qr=int(qr_orientation),
                    upright=1,
                    turned_right=2,
                    turned_left=4,
                    upside_down=3,
                )

        northwest_orientation = None
        qr = qr_code_data.get("NW")
        if qr:
            qr_orientation = qr.get("quadrant")
            if qr_orientation is not None:
                northwest_orientation = cls._check_corner(
                    val_from_qr=int(qr_orientation),
                    upright=2,
                    turned_right=3,
                    turned_left=1,
                    upside_down=4,
                )

        southeast_orientation = None
        qr = qr_code_data.get("SE")
        if qr:
            qr_orientation = qr.get("quadrant")
            if qr_orientation is not None:
                southeast_orientation = cls._check_corner(
                    val_from_qr=int(qr_orientation),
                    upright=4,
                    turned_right=1,
                    turned_left=3,
                    upside_down=2,
                )

        southwest_orientation = None
        qr = qr_code_data.get("SW")
        if qr:
            qr_orientation = qr.get("quadrant")
            if qr_orientation is not None:
                southwest_orientation = cls._check_corner(
                    val_from_qr=int(qr_orientation),
                    upright=3,
                    turned_right=4,
                    turned_left=2,
                    upside_down=1,
                )

        # make sure at least one corner is truthy, and they all agree
        truthy_results = [
            corner
            for corner in [
                northeast_orientation,
                northwest_orientation,
                southwest_orientation,
                southeast_orientation,
            ]
            if corner
        ]

        result_vals = set(truthy_results)
        if len(result_vals) != 1:
            raise RuntimeError("Unable to determine page orientation.")

        return truthy_results[0]

    @staticmethod
    def _check_corner(
        val_from_qr: int,
        upright: int,
        turned_right: int,
        turned_left: int,
        upside_down: int,
    ) -> str:
        """Check a page corner for its actual orientation.

        Args:
            val_from_qr: one of 1, 2, 3, 4.
            upright: the quadrant value for an upright orientation,
                one of 1, 2, 3, 4.
            turned_right: value for a turned_right orientation
            turned_left: value for a turned_left orientation
            upside_down: value for an upside_down orientation

        Returns:
            String describing the orientation.
        """
        if val_from_qr == upright:
            return "upright"
        elif val_from_qr == turned_right:
            return "turned_right"
        elif val_from_qr == turned_left:
            return "turned_left"
        elif val_from_qr == upside_down:
            return "upside_down"
        raise RuntimeError("Tertium non datur")

    @classmethod
    def get_rotation_angle_from_QRs(cls, qr_data: dict[str, dict[str, Any]]) -> int:
        """Get the current orientation of a page-image using its parsed QR code data.

        If it isn't upright, return the angle by which the image needs
        to be rotated, in degrees counter-clockwise.  Note this only
        deals with multiples of 90 degrees: fractional rotations are
        handled elsewhere (namely in "Rectangle Extraction").

        Args:
            qr_data: parsed QR code data.

        Returns:
            Integer rotation angle by which the page needs to be rotated.
            If page is already upright, rotation angle of 0 is returned.

        Raises:
            RuntimeError: something inconsistent in the QR data.
        """
        orientation = cls.get_page_orientation(qr_data)

        if orientation == "upright":
            return 0

        if orientation == "turned_right":
            rotate_angle = 90
        elif orientation == "turned_left":
            rotate_angle = -90
        else:
            rotate_angle = 180

        return rotate_angle

    @classmethod
    def get_rotation_angle_or_None_from_QRs(
        cls, qr_data: dict[str, dict[str, Any]]
    ) -> int | None:
        """Get the current orientation or None of a page-image using its parsed QR code data.

        If it isn't upright, return the angle by which the image needs to be rotated,
        in degrees counter-clockwise.

        Args:
            qr_data: parsed QR code data.

        Returns:
            Rotation angle by which the page needs to be rotated.
            If page is already upright, rotation angle of 0 is returned.
            Returns None if the orientation cannot be determined.
            See also also ``get_page_orientation``, although these two
            methods should perhaps converge in the future (TODO).
        """
        try:
            return cls.get_rotation_angle_from_QRs(qr_data)
        except RuntimeError:
            # We cannot get the page orientation
            return None

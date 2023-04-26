# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from plom.scan import rotate_bitmap


class PageImageProcessor:
    """
    Functions for processing a page-image: rotation
    (TODO: gamma correction, etc?)
    """

    def get_page_orientation(self, qr_code_data):
        """
        Return a string representing a page orientation. The choices are:
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
            qr_code_data: (dict) data parsed from page-image QR codes
        """

        northeast_orientation = None
        if "NE" in qr_code_data:
            expected_corner = qr_code_data["NE"]["quadrant"]
            northeast_orientation = self.check_corner(
                val_from_qr=expected_corner,
                upright="1",
                turned_right="2",
                turned_left="4",
                upside_down="3",
            )

        northwest_orientation = None
        if "NW" in qr_code_data:
            expected_corner = qr_code_data["NW"]["quadrant"]
            northwest_orientation = self.check_corner(
                val_from_qr=expected_corner,
                upright="2",
                turned_right="3",
                turned_left="1",
                upside_down="4",
            )

        southeast_orientation = None
        if "SE" in qr_code_data:
            expected_corner = qr_code_data["SE"]["quadrant"]
            southeast_orientation = self.check_corner(
                val_from_qr=expected_corner,
                upright="4",
                turned_right="1",
                turned_left="3",
                upside_down="2",
            )

        southwest_orientation = None
        if "SW" in qr_code_data:
            expected_corner = qr_code_data["SW"]["quadrant"]
            southwest_orientation = self.check_corner(
                val_from_qr=expected_corner,
                upright="3",
                turned_right="4",
                turned_left="2",
                upside_down="1",
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

    def check_corner(
        self, val_from_qr, upright, turned_right, turned_left, upside_down
    ):
        """
        Check a page corner for its actual orientation.

        Args:
            val_from_qr: (str) one of "1", "2", "3", "4"
            upright: (str) the quadrant value for an upright orientation,
                           one of "1", "2", "3", "4"
            turned_right: (str) value for a turned_right orientation
            turned_left: (str) value for a turned_left orientation
            upside_dow: (str) value for an upside_down orientation
        """
        if val_from_qr == upright:
            return "upright"
        elif val_from_qr == turned_right:
            return "turned_right"
        elif val_from_qr == turned_left:
            return "turned_left"
        elif val_from_qr == upside_down:
            return "upside_down"

    def rotate_page_image(self, path, qr_data):
        """
        Get the current orientation of a page-image using its parsed QR code
        data. If it isn't upright, rotate the image and replace it on disk.

        Args:
            path (str/pathlib.Path): path to image file
            qr_data (dict): parsed QR code data

        Returns:
            int: rotation angle by which the page was rotated.
            If page was not rotated, rotation angle of 0 is returned.
        """
        try:
            orientation = self.get_page_orientation(qr_data)
        except RuntimeError:
            # We cannot get the page orientation, so just return 0.
            return 0

        if orientation == "upright":
            return 0

        if orientation == "turned_right":
            rotate_angle = 90
        elif orientation == "turned_left":
            rotate_angle = -90
        else:
            rotate_angle = 180

        rotate_bitmap(path, rotate_angle)
        return rotate_angle

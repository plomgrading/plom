# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

import numpy as np
from PIL import Image, ImageDraw
from plom.scan import rotate_bitmap, pil_load_with_jpeg_exif_rot_applied


class PageImageProcessor:
    """Functions for processing a page-image: rotation.

    (TODO: gamma correction, etc?)
    """

    def get_page_orientation(self, qr_code_data):
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
        """Check a page corner for its actual orientation.

        Args:
            val_from_qr (str): one of "1", "2", "3", "4"
            upright (str): the quadrant value for an upright orientation,
                           one of "1", "2", "3", "4"
            turned_right (str): value for a turned_right orientation
            turned_left (str): value for a turned_left orientation
            upside_down (str): value for an upside_down orientation
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
        """Get the current orientation of a page-image using its parsed QR code data.

        If it isn't upright, rotate the image and replace it on disk.

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

    def get_rotation_angle_from_qrs(qr_dict):
        """
        Determine the correction rotation angle for an image calculated from the qr_data

        Args:
            qr_data (dict): parsed QR code data

        Returns:
            float: rotation angle (in radians) by which the page needs to be rotated CCW
            in order to correct the page's skewness. It is anticipated
            that this angle is around 5 degrees.
            If there is not enough QR data to determine the angle, return 0.
        """
        if qr_dict["SW"] and qr_dict["SE"]:
            leg = qr_dict["SW"]["y_coord"] - qr_dict["SE"]["y_coord"]
            hyp = np.sqrt(
                leg**2 + (qr_dict["SW"]["x_coord"] - qr_dict["SE"]["x_coord"]) ** 2
            )
        elif qr_dict["SE"] and qr_dict["NE"]:
            leg = qr_dict["SE"]["x_coord"] - qr_dict["NE"]["x_coord"]
            hyp = np.sqrt(
                leg**2 + (qr_dict["SE"]["y_coord"] - qr_dict["NE"]["y_coord"]) ** 2
            )
        elif qr_dict["NW"] and qr_dict["SW"]:
            leg = qr_dict["SW"]["x_coord"] - qr_dict["NW"]["x_coord"]
            hyp = np.sqrt(
                leg**2 + (qr_dict["SW"]["y_coord"] - qr_dict["NW"]["x_coord"]) ** 2
            )
        elif qr_dict["NE"] and qr_dict["NW"]:
            leg = qr_dict["NW"]["y_coord"] - qr_dict["NE"]["y_coord"]
            hyp = np.sqrt(
                leg**2 + (qr_dict["NW"]["x_coord"] - qr_dict["NE"]["x_coord"]) ** 2
            )
        else:
            # not enough QR coordinates: cannot determine angle of rotation
            return 0
        return np.arcsin(-leg / hyp)

    def determine_qr_boundary(qr_info):
        """
        Determine the corners of the L-shape defined by the QR centre coordinates

        Args:
            qr_data (dict): parsed QR code data, assumed to include (NE, SW, SE) or (NW, SW, SE)

        Returns:
            tuple (tuple of floats): extracts the (top_left, top_right, bottom_left, bottom_right)
            (x, y) pairs that describe the corresponding bounds of the rectangle defined by the QR
            coordinates. Returns None for the stapled corner which is missing a QR.
        """
        if "NW" in qr_info.keys():
            top_left = (qr_info["NW"]["x_coord"], qr_info["NW"]["y_coord"])
        else:
            top_left = None

        if "NE" in qr_info.keys():
            top_right = (qr_info["NE"]["x_coord"], qr_info["NE"]["y_coord"])
        else:
            top_right = None

        bottom_left = (qr_info["SW"]["x_coord"], qr_info["SW"]["y_coord"])
        bottom_right = (qr_info["SE"]["x_coord"], qr_info["SE"]["y_coord"])

        return (top_left, top_right, bottom_left, bottom_right)

    def draw_qr_boundary(image_path, top, left, bottom, right):
        """
        Draw a rectangle on the image file (modifying on disk) for debugging purposes

        Args:
            img_path (str/pathlib.Path): path to image file
        """
        box_location = [
            (left, top),
            (right, bottom),
        ]
        img = Image.open(img_path)
        out_img = ImageDraw.Draw(img)
        out_img.rectangle(box_location, outline="blue", width=10)
        img.save(img_path)

    def apply_coord_transformation(coord_tuple, angle, img_width, img_height):
        """
        Given an the corner coordinates, apply an affine transformation to correct them

        Args:
            coord_tuple (tuple of tuples): original coordinate values prior to transformation
            angle (float): angle that the image was rotated (in radians)
            img_width (int): width of the image that was rotated
            img_height (int): height of the image that was rotated

        Returns:
            tuple of tuples: the resulting coordinates after the affine tranformation was applied
        """
        move_to_origin = np.array(
            [[1, 0, img_width / 2.0], [0, 1, img_height / 2.0], [0, 0, 1]]
        )
        rotation = np.array(
            [
                [np.cos(angle), np.sin(angle), 0],
                [-np.sin(angle), np.cos(angle), 0],
                [0, 0, 1],
            ]
        )
        move_back = np.array(
            [[1, 0, -img_width / 2.0], [0, 1, -img_height / 2.0], [0, 0, 1]]
        )
        aff_transf = move_to_origin @ rotation @ move_back

        new_coords = list()
        for point in coord_tuple:
            if point is not None:
                p = np.array([point[0]], [point[1]], [0])
                result = aff_tranf @ p
                new_coords.append((result[0], result[1]))

        return tuple(new_coords)

    def get_rectangular_region(
        image_path, orientation, qr_dict, top_left, bottom_right
    ):
        """
        Given an image, get a particular subset of it, after applying an affine transformation to correct it

        Args:
            img_path (PIL.Image): image object that will be transformed
            qr_data (dict): parsed QR code data
            top_left (tuple): fractional values in [0, 1] which define the top left corner
                              of the desired subsection of the image
            bottom_right (tuple): same as top_left, but for the bottom right corner

        Returns:
            PIL.Image: the requested subsection of the original image
        """
        img = pil_load_with_jpeg_exif_rot_applied(image_path)
        img.rotate(orientation)

        angle = get_rotation_angle_from_qrs(qr_dict)
        new_img = img.rotate(
            angle, center=(img.width / 2.0, img.height / 2.0), resample=Image.BILINEAR
        )

        coord_tuples = determine_qr_boundary(qr_dict)
        new_coords = apply_coord_transformation(
            coord_tuples, angle, img.width, img.height
        )

        region_width = new_coords[3][0] - new_coords[0][0]
        region_height = new_coords[3][1] - new_coords[0][1]

        left = new_coords[0][0] + top_left[0] * region_width
        top = new_coords[0][1] + top_left[1] * region_height
        right = new_coords[0][0] + bottom_right[0] * region_width
        bottom = new_coords[0][1] + bottom_right[1] * region_height

        return img.crop((left, top, right, bottom))

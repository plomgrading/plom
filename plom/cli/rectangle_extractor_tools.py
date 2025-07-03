# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from plom.cli import with_messenger
from plom.plom_exceptions import PlomAuthenticationException


@with_messenger
def extract_rectangle(
    version: int,
    page_num: int,
    paper_num: int,
    region: dict[str, float],
    out_path: str | None,
    *,
    msgr,
) -> bool:
    """Extract rectangular region from a paper of the given version and page number.

    Args:
        version: the version of the page whose region will be extracted.
        page_num: the page number in the paper to be extracted.
        paper_num: the paper number to be extracted.
        region: a dict representing the rectangular region, and has these keys:
            ["left", "top", "right", "bottom"], each mapping to the coordinate value
            relative to QR position.
        out_path: The output path where the image file will be saved at. If this is None,
            then it will be saved at "./extracted_region_V{version}_page{page_num}_paper{paper_num}.png".

    Keyword Args:
        msgr:  An active Messenger object.

    Returns:
        True if the server successfully provides the image Bytes of the extracted regions.
    """
    try:
        if out_path and not out_path.endswith(".png"):
            raise ValueError(f"Output path must be a .png file, got: {out_path}")

        out_path = (
            f"extracted_region_V{version}_page{page_num}_paper{paper_num}.png"
            if not out_path
            else out_path
        )

        image_bytes = msgr.rectangle_extraction(version, page_num, paper_num, region)

        with open(out_path, "wb") as f:
            f.write(image_bytes)

        print(f"Extracted region saved at: {out_path}")
        return True

    except (PlomAuthenticationException, ValueError) as e:
        print(f"Error: {e}")
        return False

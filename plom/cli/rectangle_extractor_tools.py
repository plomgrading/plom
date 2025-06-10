# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from plom.cli import with_messenger
from plom.plom_exceptions import PlomAuthenticationException


@with_messenger
def extract_rectangle(
    version: int, page_num: int, region: dict[str, float], out_path: str | None, *, msgr
) -> bool:
    """Extract rectangular region from papers of the given version and page number.

    The successfully extracted region is saved as a zip file.

    Note: the zip may be empty when there are no papers of such version and page_num.

    Args:
        version: the version of the page whose region will be extracted.
        page_num: the page number in the paper to be extracted.
        region: a dict representing the rectangular region, and has these keys:
            ["left", "top", "right", "bottom"], each mapping to the coordinate value
            relative to QR position.
        out_path: The output path where the zip file will be saved at. If this is None,
        then it will be saved at "./extracted_region.zip".

    Keyword Args:
        msgr:  An active Messenger object.

    Returns:
        True if the server successfully provides the zip Bytes of the extracted regions.
    """
    try:
        if out_path and not out_path.endswith(".zip"):
            raise ValueError(f"Output path must be a .zip file, got: {out_path}")

        out_path = "extracted_region.zip" if not out_path else out_path

        zip_content = msgr.rectangle_extraction(version, page_num, region)
        with open(out_path, "wb") as f:
            f.write(zip_content.getvalue())
        print(f"Extracted region zip saved at: {out_path}")
        return True

    except (PlomAuthenticationException, ValueError) as e:
        print(f"Error: {e}")
        return False

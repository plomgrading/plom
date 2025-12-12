# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2020-2025 Colin B. Macdonald

import logging
from multiprocessing import Pool

from tqdm import tqdm

from plom.tpv_utils import getPosition
from plom.scan import QRextract_legacy
from plom.scan.rotate import rotate_bitmap
from plom.scan import PlomImageExts


log = logging.getLogger("scan")


def decode_QRs_in_image_files(where):
    """Find all bitmaps in pageImages dir and decode their QR codes.

    If their QRcodes have not been successfully decoded previously
    then decode them.  The results are stored in blah.<ext>.qr files.

    Args:
        where (str, Path): where to search, e.g., "bundledir/pageImages"
    """
    stuff = []
    for ext in PlomImageExts:
        stuff.extend(where.glob(f"*.{ext}"))
    N = len(stuff)
    with Pool() as p:
        _ = list(tqdm(p.imap_unordered(QRextract_legacy, stuff), total=N))
    # This does the same as the following serial loop but in parallel
    # for x in glob.glob(...):
    #     QRextract_legacy(x)


def reOrientPage(fname, qrs):
    """Re-orient this page if needed, changing the image file on disk.

    If a page is upright, a subset of the QR codes 1 through 4 are on
    the corners:

        2---1   NW---NE
        |   |    |   |
        |   |    |   |
        3---4   SW---SE

    We use this known configuration to recognize rotations.  Either 1
    or 2 is missing (because of the staple area) and we could be
    missing others.

    Assuming reflection combined with missing QR codes is an unlikely
    scenario, we can orient even if we know only one corner.

        1----4    4---3    3----2
        |    |    |   |    |    |
        2----3    |   |    4----1
                  1---2

    Args:
       fname (str): the bitmap filename of this page.  Either its the FQN
                    or we are currently in the right directory.
       qrs (dict): the QR codes of the four corners.  Some or all may
                   be missing.

    Returns:
       bool: True if the image was already upright or has now been
             made upright.  False if the image is in unknown
             orientation or we have contradictory information.
    """
    targets = {
        "upright": [1, 2, 3, 4],  # [NE, NW, SW, SE]
        "rot90cw": [2, 3, 4, 1],
        "rot90cc": [4, 1, 2, 3],
        "flipped": [3, 4, 1, 2],
    }
    # "actions" refer to the CCW rotation we apply to fixed the observed
    # rotation.  E.g., if we observe "rot90cc" then we need to perform a
    # 90 cw rotation, which is -90 ccw; the value of the action.
    actions = {
        "upright": 0,
        "rot90cw": 90,
        "rot90cc": -90,
        "flipped": 180,
    }

    # fake a default_dict, flake8 does not like, consider using function
    g = lambda x: getPosition(qrs.get(x)) if qrs.get(x, None) else None  # noqa: E731
    current = [g("NE"), g("NW"), g("SW"), g("SE")]

    def comp(A, B):
        """Compare two lists ignoring any positions with Nones."""
        return all([x == y for x, y in zip(A, B) if x and y])

    matches = {k: comp(v, current) for (k, v) in targets.items() if comp(v, current)}
    if len(matches) != 1:
        return False
    match_key, v = matches.popitem()
    rotate_bitmap(fname, actions[match_key])
    return True

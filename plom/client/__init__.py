# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald

"""Plom client and supporting functions."""

__copyright__ = "Copyright (C) 2018-2024 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"


from plom import __version__
from .marker import MarkerClient
from .identifier import IDClient
from .chooser import Chooser
from .random_marking_utils import do_rando_marking
from .random_identifying_utils import do_rando_identifying
from .image_view_widget import ImageViewWidget

# what you get from "from plom.client import *"
__all__ = ["MarkerClient", "IDClient", "Chooser"]

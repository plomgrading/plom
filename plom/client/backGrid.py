# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2023, 2025 Colin B. Macdonald

from importlib import resources
from time import localtime

from PyQt6.QtGui import QBrush, QPixmap

import plom.client


class BackGrid(QBrush):
    def __init__(self, username=None):
        super().__init__()
        # set the area outside the groupimage to be tiled grid png
        # generally disabled as we just use the window background
        if localtime().tm_mon == 4 and localtime().tm_mday == 1:
            pm = QPixmap()
            res = resources.files(plom.client) / "backGrid2.png"
            pm.loadFromData(res.read_bytes())
            self.setTexture(pm)
        # else:
        #     pm = QPixmap()
        #     pm.loadFromData(resources.read_binary(plom.client, "backGrid1.svg"))
        #     self.setTexture(pm)

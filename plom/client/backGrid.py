# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from importlib.resources import files
from time import localtime
from PyQt5.QtGui import QBrush, QPixmap


class BackGrid(QBrush):
    def __init__(self, username=None):
        super().__init__()
        # set the area outside the groupimage to be tiled grid png
        # generally disabled as we just use the window background
        if localtime().tm_mon == 4 and localtime().tm_mday == 1:
            self.setTexture(QPixmap(str(files("plom.client") / "backGrid2.png")))
        else:
            self.setTexture(QPixmap(str(files("plom.client") / "backGrid1.svg")))

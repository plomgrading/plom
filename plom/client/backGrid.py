#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys
from time import localtime
from PyQt5.QtGui import QBrush, QPixmap


class BackGrid(QBrush):
    def __init__(self, username=None):
        # init the qgraphicsview
        super(BackGrid, self).__init__()
        # set the area outside the groupimage to be tiled grid png
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(__file__)
        if (localtime().tm_mon == 4 and localtime().tm_mday == 1) or (
            username
            and any(x in username.lower() for x in ["omer", "remo", "legna", "angel"])
        ):
            self.setTexture(QPixmap(os.path.join(base_path, "backGrid2.png")))
        # else:
        #    self.setTexture(QPixmap(os.path.join(base_path, "backGrid1.svg")))

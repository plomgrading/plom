# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from time import localtime
import platform

if platform.sys.version.split()[0]>='3.7':
    import importlib.resources as resources
else:
    import importlib_resources as resources

from PyQt5.QtGui import QBrush, QPixmap

# TODO: does the string form work with Pyinstaller?
# import plom.client


class BackGrid(QBrush):
    def __init__(self, username=None):
        super().__init__()
        # set the area outside the groupimage to be tiled grid png
        # generally disabled as we just use the window background
        if localtime().tm_mon == 4 and localtime().tm_mday == 1:
            self.setTexture(
                QPixmap(str(resources.files("plom.client") / "backGrid2.png"))
            )
        else:
            self.setTexture(
                QPixmap(str(resources.files("plom.client") / "backGrid1.svg"))
            )

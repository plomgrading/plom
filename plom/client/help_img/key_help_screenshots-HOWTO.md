# SPDX-License-Identifier: FSFAP
# Copyright (C) 2023 Colin B. Macdonald


How to create the screenshot graphics for Key Help dialog
=========================================================

* Turn off anti-aliasing in OS (I used gnome-tweaks)

* Change Qt theme to high-contrast
  ```diff
  -    app.setStyle(QStyleFactory.create("Fusion"))
  +    app.setStyle(QStyleFactory.create("HighContrast"))
  ```

* Set Plom fontsize bigger.  I used 16 but 14 might be better next time for
  buttons to line up.

* Screenshot, with a few white pixel border

* The buttons have hairline thicknesses that are poor with bilinear scaling in
  QGraphicsScene so we do some extra editing:

* In the future, screenshotting on a HighDPI display would be enough.

* Open in Gimp
  - select white area (magic colour tool)
  - Select -> border -> 1px
  - Ctrl-X to cut a black border around each
  - paste a black layer underneigh
  - clean up boundary (likely got a black border from bordering operation)
  - convert to greyscale
  - flatten layers
  - remove transparency
  - reduce from 8-bit to say 64 colours (check file size!)
  - resize to 640pixels wide with cubic interp
  - export as PNG

* `pngcrush` and `optipng` did not make enough difference to bother.

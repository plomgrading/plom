#!/usr/bin/env bash

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Aidan Murphy

## How to generate plomLogo.png and plomLogoDark.png

# install inkscape
# e.g. `sudo apt install inkscape`

# generate plomLogo.png with this inkscape command:
inkscape plomLogo.svg --export-type png --export-filename plomLogo.png --export-width 276 --export-height 93

# To get plomLogoDark.png:
# - change the hex colour of the "Plom" text in the plomLogo.svg from #000000 to #aeb2b6
#   in a text editor.
# - execute the same command with a different export-filename:
#   inkscape plomLogo.svg --export-type png --export-filename plomLogoDark.png --export-width 276 --export-height 93
# - revert the hex colour change.

# TODO: inkscape accepts a --pipe param, I couldn't get it to work, but possibly:
# sed "s/fill:#000000/fill:#aeb2b6/" plomLogo.svg | inkscape --pipe --export-type png --export-filename plomLogoDark.png --export-width 276 --export-height 93

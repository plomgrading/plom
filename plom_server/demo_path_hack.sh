#!/usr/bin/env bash

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna

set -e

# able to get the `plom` module even if not installed.
export PYTHONPATH=".."

# old way
# python3 manage.py plom_demo $@

# new way
./Launcher/launch_scripts/launch_plom_demo_server.py $@

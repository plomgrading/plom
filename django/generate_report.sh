#!/usr/bin/env bash

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

export PYTHONPATH=".."
export DJANGO_SETTINGS_MODULE=Web_Plom.settings

python Finish/management/commands/generate_report.py

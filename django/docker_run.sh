#!/bin/bash
# SPDX-License-Identifier: FSFAP
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

python3 manage.py plom_demo --no-waiting
python3 manage.py runserver 0.0.0.0:8000

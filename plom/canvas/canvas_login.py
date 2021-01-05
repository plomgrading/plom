#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Colin B. Macdonald
# Copyright (C) 2020 Forest Kobayashi

"""TODO: Make all the login stuff happen automatically, maybe using
OAuth
"""


# Import the Canvas class
from canvasapi import Canvas

# Canvas API URL
# TODO: Make this general
API_URL = "https://canvas.ubc.ca"

# Get my API key out of the secrets file
# TODO: Make this general
from .api_secrets import fk_key as API_KEY
from .api_secrets import sbox_id as sbox_id

canvas = Canvas(API_URL, API_KEY)

# Delete API_KEY so that it can't be accessed outside of this call
del API_KEY

# Uncomment to get a list of courses. Note, canvas.get_courses()
# returns an object of type PaginatedList by default, which is
# lazily-evaluated. We do `list(courses)` to just get the full list.
# courses = canvas.get_courses()
# clist = list(courses)
# print(clist)

## The part below is really just hard-coded for the purposes of making
## an example. Really, we want to get the userid / etc. by doing the
## OAuth login stuff.

# Get Colin's Sandbox
sbox = canvas.get_course(sbox_id)

user = canvas.get_current_user()

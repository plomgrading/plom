# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Colin B. Macdonald

#!/bin/sh

# Here is the very manual process of keeping all our dependencies up-to-date
# Circa 2026-January

# `pip install bumper`
bump --file requirements.txt
# then manually merge some.  Often it rearranges them :(

# The rest are all done manually :(

# here I remove the entire plom_extra_static/ dir
# then bump the version numbers by a bunch of many copy-pasting into browser
# then I run the script, and update the sha256 based on the scripts failures
echo "[ ] plom_server/get_js.py"

# I usually try to bump ruff etc in .gitlab-ci at the same time for consistency
echo "[ ] pre-commit autoupdate"

# here I grep for "~=" and manually update based on looking at PyPI
echo "[ ] .gitlab-ci.yaml"

# check docker documentation
echo "[ ] .gitlab-ci.yaml: docker"

echo "[ ] compose.yaml example: nginx and postgres pins"

echo "[ ] Containerfile"

#!/bin/bash
# SPDX-License-Identifier: FSFAP
# Copyright (C) 2023-2024 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

# set server binding port
if [[ -z $PLOM_CONTAINER_PORT ]]; then
	PORT="8000"
else
	PORT=$PLOM_CONTAINER_PORT
fi

# DEPRECATION NOTICE: this might be deprecated, or at least we're trying to move away from
# it as of March 2025.

if ! python3 manage.py plom_database --check-for-database; then
	echo "DOING A HOT START (we already have a database)"
	echo "Issue #3299: Please note this merely checks for the *existence* of"
	echo "a database; it does not yet check anything about the filesystem."
	echo "Use this hot start feature at your own peril."
	if [ "x$PLOM_DEBUG" = "x0" ]; then
		python3 plom_server/scripts/launch_plom_server.py --production --port $PORT --hot-start
	else
		python3 plom_server/scripts/launch_plom_server.py --development --port $PORT --hot-start
	fi
else
	echo "No existing database; starting from scratch"
	# start either a canned demo or an empty server
	if [[ "$PLOM_DEMO" -eq 1 ]]; then
		if [ "x$PLOM_DEBUG" = "x0" ]; then
			python3 plom_server/scripts/launch_plom_demo_server.py --production --port $PORT --stop-after bundles-pushed
		else
			python3 plom_server/scripts/launch_plom_demo_server.py --development --port $PORT --stop-after bundles-pushed
		fi
	else
		if [ "x$PLOM_DEBUG" = "x0" ]; then
			python3 plom_server/scripts/launch_plom_server.py --production --port $PORT
		else
			python3 plom_server/scripts/launch_plom_server.py --development --port $PORT
		fi
	fi
fi

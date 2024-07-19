#!/bin/bash
# SPDX-License-Identifier: FSFAP
# Copyright (C) 2023-2024 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

# set server binding port
if [[ -z $PLOM_CONTAINER_PORT ]]; then
	PORT="8000"
else
	PORT=$PLOM_CONTAINER_PORT
fi

# in production mode, there are additional steps for static files
if [ "x$PLOM_DEBUG" = "x0" ]; then
	python3 manage.py collectstatic --clear --no-input
fi

if ! python3 manage.py plom_database --check-for-database; then
	echo "DOING A HOT START (we already have a database)"
	echo "Issue #3299: Please note this merely checks for the *existence* of"
	echo "a database; it does not yet check anything about the filesystem."
	echo "Use this hot start feature at your own peril."
else
	echo "No existing database; starting from scratch"
	# start either a canned demo or an empty server
	if [[ "$PLOM_DEMO" -eq 1 ]]; then
		python3 manage.py plom_demo --no-waiting
	else
		# clean up old db etc and build a new one
		python manage.py plom_clean_all_and_build_db
		# now make groups and first users
		python manage.py plom_make_groups_and_first_users
	fi
fi

# We need a Huey queue: start one in the background
python3 manage.py djangohuey &

# Finally launch the server itself
if [ "x$PLOM_DEBUG" = "x0" ]; then
	gunicorn Web_Plom.wsgi --bind 0.0.0.0:$PORT
else
	python3 manage.py runserver 0.0.0.0:$PORT
fi

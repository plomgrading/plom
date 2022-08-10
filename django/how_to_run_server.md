# How to run the server

(WIP instructions)

## Install requirements and download the repo

We need to install any required python packages and get the actual webplom repo... and switch to the working branch which is "dev".

1. Clone the WebPlom repo
2. [Set up a virtual environment](https://docs.python.org/3/library/venv.html) 
3. `source env/bin/activate`
4. Install libraries with pip: 
```
django
django-braces
pymupdf
toml
model_bakery (for tests)
beautifulsoup4 (HTML parsing)
django-session-timeout
django-htmx
```
5. Switch to the dev branch: `git checkout dev`

## Initalise the database
Django needs you to set up all the database tables.

1. Run `python3 manage.py migrate` to setup the database

## Setting up groups and users
Django wants a "super user" to do administrative stuff - they can
access everything. Plom then requires several different groups of
users - admin, manager, marker and scanner. So we need to create those
groups and add the super-user into the admin group.

1. Run `python3 manage.py createsuperuser` to create an admin account (email address is optional)
2. Run `python3 manage.py creategroups` to automatically create admin, manager, marker, and scanner groups. Then, any superusers will be added to the admin group.

Note that if you accidentally do (2) before (1) then you can just run (2) again and it will skip the create-groups bit and just add the superuser to the admin group.

## Running the server

1. To launch the server: `python3 manage.py runserver`

## Create a manager
1. Still logged in as the admin, go to the homepage `<local_url>/` and click on "sign up manager"
2. Fill out the form and copy the generated link
3. Sign out from the admin account and follow the copied link to the manager password change form
4. Once it's done, you should be redirected to the manager homepage


# For testing

## Run inbuilt tests

1. To run tests: `python3 manage.py test`




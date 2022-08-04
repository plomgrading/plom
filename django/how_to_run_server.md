# How to run the server

(WIP instructions)

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
```
5. Switch to the dev branch: `git checkout dev`
6. To launch the server: `python3 manage.py runserver`
8. To run tests: `python3 manage.py test`

## Init the database
1. Run `python3 manage.py migrate` to setup the database

## Setting up users
1. Run `python3 manage.py creategroups` to automatically create admin, manager, marker, and scanner groups. Then, superusers will be added to the admin group.
2. Run `python3 manage.py createsuperuser` to create an admin account (email address is optional)

## Create a manager
1. Still logged in as the admin, go to the homepage `<local_url>/` and click on "sign up manager"
2. Fill out the form and copy the generated link
3. Sign out from the admin account and follow the copied link to the manager password change form
4. Once it's done, you should be redirected to the manager homepage

# How to run the server

(WIP instructions)

1. Clone the WebPlom repo
2. [Set up a virtual environment](https://docs.python.org/3/library/venv.html) 
3. `source env/bin/activate`
4. Install libraries with pip: 
```
django
django-braces
django-utils-six
pymupdf
toml
model_bakery (for tests)
```
5. Switch to the dev branch: `git checkout dev`
6. To launch the server: `python3 manage.py runserver`
7. To run tests: `python3 manage.py tests`

## Init the database
1. Run `python3 manage.py migrate` to setup the database

## Setting up users
1. Run `python3 manage.py createsuperuser` to create an admin account (email address is optional)
2. Before signing in, go to `<local_url>/admin` on the browser and sign in with the admin username/password
3. Go to Authentication and Authorization > Groups and select "Add group" in the top-right corner
4. Create a new group called `admin` (case sensitive) and save (without adding any permissions to it from the table)
5. Create another group called `manager` and save, also without touching the permissions table
6. Go to Authentication and Authorization > Users and select the admin user (should be the only user in the table)
7. Scroll to Permissions > Groups, add the admin user to the `admin` group, and save

## Create a manager
1. Still logged in as the admin, go to the homepage `<local_url>/` and click on "sign up manager"
2. Fill out the form and copy the generated link
3. Sign out from the admin account and follow the link to the manager password change form
4. Once it's done, you should be redirected to the manager homepage

# WebPlom


# How to run the server

(WIP instructions)

## Install requirements and download the repo

We need to install any required python packages and get the actual webplom repo... and switch to the working branch which is "dev".

1. Clone the WebPlom repo
2. [Set up a virtual environment](https://docs.python.org/3/library/venv.html) 
3. `source env/bin/activate`
4. Install all necessary libraries using the command below:<br>
`pip install -r requirements.txt`

5. Switch to the dev branch: `git checkout dev`

## Clean up any old migrations
In case they cause you any headaches, you can clean up any old migrations using the
pip package 'django-reset-migrations'.
1. Run `python3 manage.py reset_migrations Authentication Preparation TestCreator`

**Note** The above needs to be run on any django app that has any db-models in it. Make sure the above
command is updated when more apps are added.

## Initialise the database
Django needs you to set up all the database tables.

1. Run `python3 manage.py migrate` to setup the database

## Setting up groups and users
Django wants a "super user" to do administrative stuff - they can
access everything. Plom then requires several different groups of
users - admin, manager, marker and scanner. So we need to create those
groups and add the super-user into the admin group.

1. Run `python3 manage.py createsuperuser` to create an admin account (email address is optional)
2. Run `python3 manage.py plom_create_groups` to automatically create admin, manager, marker, and scanner groups. Then, any superusers will be added to the admin group.
3. (Optional) Run `python3 manage.py plom_create_demo_users` to automatically create demo users such as manager, scanners, and markers

Note that if you accidentally do (2) before (1) then you can just run (2) again and it will skip the create-groups bit and just add the superuser to the admin group.


## Running the server

1. To launch the server: `python3 manage.py runserver`

Take note of the address that it tells you the website is running at.

## Log into website as "super-user" (ie: admin user)
1. Open web-browser to "localhost:8000" or whatever the system reported in the "running the server" step above.
2. Log in using the "super-user" name and password you generated above.
3. You should be bounced to a **very** simple landing page with options in the left-hand column.

## Make a manager instructions
In order to create a manager, you need to log in as a super user.
- url: `http://localhost:8000/signup/manager/` or `http://127.0.0.1:8000/signup/manager/`
1. Log in as a super user
2. Click on "Sign Up Manager" in the left-hand column of the landing page.
3. Fill out the form and then click submit 
4. Click on "Copy" to copy the generated link
5. Click on "Log out" to sign out from the admin account
6. Open a different browser and paste the link there
7. Ctrl + v or right-click->paste onto the address bar
8. Follow the copied link to the manager password change form and click "Submit" once password entered
9. Once it's done, you should be redirected to a page to tell you to log in
10. Click on "Log in" to log in using "manager-user" name and password you created 

Note:
If you forgot the manager username you generated in step 3, log in as "super user" and click on "Password Reset Link"
to find the manager username.  

## Clear existing data from database
This is the command for wiping the existing data from DB:
`python manage.py flush`

# For testing (much to do here)

## Run inbuilt tests

1. To run tests: `python3 manage.py test`

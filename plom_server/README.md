# How to run the Plom Server

You need a PostgreSQL server, then type `plom-server`.  The rest of these instructions are
perhaps out-of-date details that should be automated by the above.
TODO: perhaps  they should be removed before bitrot further!


## Setting up PostgreSQL
You need a running PostgreSQL server. Follow the installation instructions found (here)[https://www.postgresql.org/download/].  One approach is use a container.

With PostgreSQL running, you need to complete two tasks:

1. Create a user for Plom, either using environment variables or using the default "postgres:postgres"
2. Create a table for Plom, either using environment variables or using the default "plom_db"

If you are using the defaults and running on Linux, a series of commands like the following will work. (These have been tested on Debian.) You can replace the username and database name:

1. `sudo -u postgres psql postgres`
2. `ALTER USER postgres PASSWORD 'postgres';`
3. `CREATE DATABASE plom_db;`
4. `GRANT ALL PRIVILEGES ON DATABASE plom_db TO postgres;`
5. `QUIT`

Here commands 3-5 are given inside the psql command-line interface; the others are at the Linux command prompt.
If step 2 triggers an error message from `psql`, try `CREATE USER postgres WITH PASSWORD 'postgres';` instead before continuing.

## Initialize the database

This takes two steps. Enter these commands at the shell prompt.

1. `python3 manage.py makemigrations`
2. `python3 manage.py migrate`

These commands are non-interactive. Just hope they complete successfully.

## Setting up groups and users

1. Run `python3 manage.py plom_make_groups_and_first_users` to automatically create the various user account groups.
2. (Optional) Run `python3 manage.py plom_create_demo_users` to automatically create demo users such as manager, scanners, and markers.


## Misc other setup

`python3 manage.py plom_get_static_javascript` pre-downloads javascript and other static resources.

TODO: also something about `collectstatic` if doing production run.


## Running the server

1. To launch the server: `python3 manage.py runserver`

Take note of the address that it tells you the website is running at.

## Log into website with your superuser
1. Open web-browser to "http://localhost:8000" or whatever the system reported in the "running the server" step above.
2. Log in using the name and password of your superuser, as defined above. You should see a very short menu in the left navigation bar.


## Make a manager

Earlier steps should have created a user named manager and other demo users. If you skipped those, here is an alternative approach.

1. Log in as the admin user (superuser)
2. Go to "Users" and click "create new users"
3. Use the form to create a new account named "manager".
4. Copy the generated link and logout of the admin account.
5. Paste the link in the browser's URL bar, or email it to a friend, etc.

Note:
If you forgot the manager username, you can login as the admin user and click on "Password Reset Link".

## Look around as manager

The user named "manager" does most of the test setup and oversight tasks. Log in using this account
to see what the system looks like.

### Notes: How to clear existing data from database
Here is the command for wiping the existing data from DB:
`python3 manage.py flush`


### Notes: How to run automated tests

To launch Django's built-in test suite, give this command at the shell prompt:
`python3 manage.py test`

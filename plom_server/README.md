# How to run the "new" Plom Server

## Setting up PostgreSQL
You need a running PostgreSQL server. Follow the installation instructions found (here)[https://www.postgresql.org/download/]. With PostgreSQL running, you need to complete two tasks:

1. Create a user for Plom, either using environment variables or using the default "postgres:postgres"
2. Create a table for Plom, either using environment variables or using the default "plom_db"

If you are using the defaults and running on Linux, a series of commands like the following will work. (These have been tested on Debian.) You can replace the username and database name:

1. `sudo su - postgres`
2. `psql postgres`
3. `CREATE ROLE postgres WITH LOGIN PASSWORD 'postgres';`
4. `CREATE DATABASE plom_db;`
5. `GRANT ALL PRIVILEGES ON DATABASE plom_db TO postgres;`
6. `QUIT`
7. `exit`

Here commands 3-6 are given inside the psql command-line interface; the others are at the Linux command prompt.
If step 3 triggers an error message from `psql`, try `ALTER USER postgres WITH PASSWORD 'postgres';` at position 3.5 before continuing.

## Initialize the database

This takes two steps. Enter these commands at the shell prompt.

1. `python3 manage.py makemigrations`
2. `python3 manage.py migrate`

These commands are non-interactive. Just hope they complete successfully.

## Setting up groups and users
Django wants a "super user" to do administrative stuff - they can
access everything. Plom then requires several different groups of
users - admin, manager, marker and scanner. So we need to create those
groups and add the super-user into the admin group.

1. Run `python3 manage.py createsuperuser` to create an admin account (email address is optional). Remember the username defined here.
2. Run `python3 manage.py plom_create_groups` to automatically create admin, manager, marker, and scanner groups. Then, any superusers will be added to the admin group.
3. (Optional) Run `python3 manage.py plom_create_demo_users` to automatically create demo users such as manager, scanners, and markers. The default password for `manager` is `1234`. For the other demo users (`demoAdmin`, `demoScanner1`, etc.), the default password is identical to the username.

Note that if you accidentally do (2) before (1) then you can just run (2) again and it will skip the create-groups bit and just add the superuser to the admin group.


## Running the server

1. To launch the server: `python3 manage.py runserver`

Take note of the address that it tells you the website is running at.

## Log into website with your superuser
1. Open web-browser to "http://localhost:8000" or whatever the system reported in the "running the server" step above.
2. Log in using the name and password of your superuser, as defined above. You should see a very short menu in the left navigation bar.


## Make a manager

Earlier steps should have created a user named manager and other demo users. If you skipped those, here is an alternative approach.

Start at the url noted under Running the Server, typically `http://localhost:8000/users`. Then ...

1. Log in as the admin user (superuser)
2. Click "create new users"
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

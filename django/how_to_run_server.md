# How to run the server

(WIP instructions)

1. Clone the WebPlom repo and switch to the dev branch
2. [Set up a virtual environment](https://docs.python.org/3/library/venv.html) 
3. `source env/bin/activate`
4. Install libraries with pip: 
```
django
django-braces
django-utils-six
pymupdf
```
5. To launch the server: `python3 manage.py runserver`
6. To run tests: `python3 manage.py tests`

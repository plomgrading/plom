Building Plom's Documentation
=============================

In the doc/ directory:
```
make autodocs
# all of the following produce different outputs, `make help` for more info
make html
make singlehtml
make latexpdf
make linkcheck
```
then display the webpages in your browser
```
firefox build/html/index.html
```

## Notes:

  * TODO: what should be the relationship between this autogen stuff
    and the official website? PrairieLearn strikes a good balance (I think),
    although it's target users are somewhat adept programmers.

  * Many projects don't use sphinx-apidoc at all; they manually populate .rst files with
    automodule / autodoc / auto... for each thing they want presented:
    [python docs](https://github.com/python/cpython/tree/main/Doc)
    using `sphinx-build` to generate html files.
    TODO: We should follow suit?

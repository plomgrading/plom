Building Plom's Documentation
=============================

In the root of the git project:
```
sphinx-apidoc -f -o doc/source plom
```
Then
```
cd doc
make html
firefox build/html/index.html
```


## Notes:

  * I'm still unclear on the `sphinx-apidoc` call versus `automodule`
    thing in side `index.rst`.

  * Should build all this on CI runs.

  * TODO: Slowly move legacy things from `docs/` to this new `doc/`.

  * TODO: what should be the relationship between this autogen stuff
    and the official website?

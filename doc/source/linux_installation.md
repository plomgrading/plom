<!--
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2022 Colin B. Macdonald"
__copyright__ = "Copyright (C) 2019-2020 Matthew Coles"
__license__ = "AGPL-3.0-or-later"
 -->

Installing on Popular GNU/Linux Distros
=======================================

For production use of Plom we recommend using Docker.  These instructions below
are mainly for developers to configure their systems.


Fedora
------

Tested on Fedora 35.  Some stuff from the package manager:
```
  # sudo dnf install \
        ImageMagick openssl zbar gcc gcc-c++ cmake \
        turbojpeg-devel libjpeg-turbo-devel python3-cffi \
        python3-passlib python3-qt5 \
        python3-jsmin python3-defusedxml python3-yaml \
        python3-more-itertools python3-chardet \
        python3-seaborn python3-cairosvg \
        python3-aiohttp python3-appdirs python3-arrow \
        python3-pillow python3-pandas python3-peewee \
        python3-PyMuPDF python3-scikit-learn \
        python3-stdiomask python3-requests-toolbelt \
        python3-pip python3-wheel python3-setuptools \
        python3-toml python3-tqdm python3-urllib3 python3-weasyprint \
        python3-pytest \
        latexmk tex-dvipng texlive-scheme-basic \
        tex-preview tex-charter tex-exam tex-preprint \
        python3-myst-parser python3-sphinx python3-sphinx_rtd_theme
```
At this point `pip install --user .` from inside the Plom source tree should pull
in the remaining dependencies.  Alternatively, you can do something like:
```
  # pip install --upgrade --user pyzbar jpegtran-cffi
```
There are additional dependencies for the machine-learning-based ID Reader:
```
  # pip install --user imutils lapsolver opencv-python-headless
```
If you're building a production server you may want to ignore some of the above
and instead use pinned versions:
```
  # pip install --user -r requirements.txt
```
You may also want to consider a tool like `virtualenv`.


Ubuntu
------

Some stuff from the package manager:
```
  # sudo apt install \
        cmake make imagemagick dvipng g++ openssl \
        libzbar0 libjpeg-turbo8-dev libturbojpeg0-dev python3-cffi \
        python3-passlib python3-pandas python3-pyqt5 python3-pytest \
        python3-dev python3-pip python3-setuptools python3-wheel \
        python3-requests-toolbelt texlive-latex-extra \
        latexmk texlive-fonts-recommended python3-pil \
        python3-tqdm libpango-1.0-0 libpangocairo-1.0-0
```
The pango stuff is needed for weasyprint.

These (and others) should work from the package manager but pip pulls them
in anyway, not sure why.
```
  # sudo apt install python3-defusedxml python3-jsmin python3-cairosvg
```

Other stuff we get from pip:
```
  # pip3 install --upgrade --user pip
  # python3 -m pip install --upgrade --user setuptools
  # python3 -m pip install --upgrade --user pymupdf weasyprint imutils toml \
        aiohttp pyzbar jpegtran-cffi peewee
  # python3 -m pip install --user imutils lapsolver opencv-python-headless
  # python3 -m pip install --user scikit-learn
```
Note `python3 -m pip` uses the newly upgraded pip (necessary at least on Ubuntu 18.04).

If you're building a production server you may want to ignore some of the above
and instead use pinned versions:
```
  # python3 -m pip install --user -r requirements.txt
```
You may also want to consider a tool like `virtualenv`.

Finally: it has been noted that ImageMagick doesn't allow hacking
of pdf files by default, some edits are needed to
`/etc/ImageMagick-6/policy.xml`.  Near the end of the file,
comment out the `pattern="PDF"` part:
```diff
   <policy domain="coder" rights="none" pattern="EPS" />
-  <policy domain="coder" rights="none" pattern="PDF" />
+  <!--<policy domain="coder" rights="none" pattern="PDF" />-->
   <policy domain="coder" rights="none" pattern="XPS" />
```

Another thing to watch out for (at least on Ubuntu 18.04) is that
`pip install --user ...` commands will install binaries in
`${HOME}/.local/bin` but this is not in your `$PATH` by default.
You may need to update your path in a file such as `.bashrc`.

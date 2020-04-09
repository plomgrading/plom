<!--
__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Colin B. Macdonald"
__license__ = "GFDL"
 -->
Installing on Popular GNU/Linux Distros
=======================================

Fedora
------

Tested on Fedora 31.  Some stuff from the package manager:
```
  # sudo dnf install ImageMagick zbar \
                     python3-passlib python3-pypng \
                     python3-jsmin python3-defusedxml python3-yaml \
                     python3-urllib3 python3-more-itertools \
                     python3-seaborn python3-matplotlib-qt5 python3-aiohttp \
                     python3-peewee python3-pandas python3-requests-toolbelt \
                     python3-pip python3-toml python3-weasyprint \
                     python3-xvfbwrapper python3-tqdm python3-pytest \
                     tex-preview tex-dvipng texlive-scheme-basic tex-xwatermark \
                     tex-charter
```

Other stuff we install locally with `pip`:
```
  # pip3 install --upgrade --user pyqrcode pyzbar pymupdf
```

More dependencies for the tensorflow-based ID reader:
```
  # sudo dnf install python3-termcolor python3-wheel python3-grpcio \
                     python3-markdown python3-h5py
  # pip3 install --user imutils lapsolver tensorflow
```


Ubuntu
------

Some stuff from the package manager:
```
  # sudo apt install \
        zbar-tools cmake make imagemagick dvipng g++ \
        python3-passlib python3-pandas python3-pyqt5 python3-pytest \
        python3-pyqt5.qtsql python3-pyqrcode python3-png python3-dev \
        python3-pip python3-setuptools python3-wheel \
        python3-requests-toolbelt python3-opencv texlive-latex-extra \
        latexmk texlive-fonts-recommended python3-peewee python3-xvfbwrapper \
        python3-tqdm libpango-1.0 libpangocairo-1.0
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
        aiohttp pyzbar
  # python3 -m pip install --upgrade --user imutils lapsolver tensorflow
```
(Note `python3 -m pip` to use the newly upgraded pip).

Ubuntu 16.04 also needs:
```
  # python3 -m pip install --user opencv-python peewee pyqrcode pypng

```

Ubuntu 16.04: running python3 maps to python3.5 by default - for script 11 run python3.6 explicitly

It also may be useful to install `x2goserver`.

Finally: it has been noted that ImageMagick doesn't allow hacking
of pdf files by default, some edits are needed to
`/etc/ImageMagick-6/policy.xml`.  Near the end of the file,
comment out the `pattern="PDF"` part:
```dif
   <policy domain="coder" rights="none" pattern="EPS" />
-  <policy domain="coder" rights="none" pattern="PDF" />
+  <!--<policy domain="coder" rights="none" pattern="PDF" />-->
   <policy domain="coder" rights="none" pattern="XPS" />
```

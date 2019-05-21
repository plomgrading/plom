<!--
__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__license__ = "GFDL"
 -->
Installing on Popular GNU/Linux Distros
=======================================

Fedora
------

Tested on Fedora 30.  Some stuff from the package manager:
```
  # sudo dnf install parallel ImageMagick zbar \
                     python3-PyMuPDF python3-passlib python3-pypng \
                     python3-jsmin python3-defusedxml python3-yaml \
                     python3-urllib3 python3-more-itertools \
                     python3-seaborn python3-matplotlib-qt5 \
                     python3-peewee python3-pandas \
```
Fedora's [python3-weasyprint is too old](https://bugzilla.redhat.com/show_bug.cgi?id=1475749).

Other stuff we install locally with `pip`:
```
  # pip3 install --upgrade --user pyqrcode easywebdav2 wsgidav \
                                  cheroot Weasyprint
```

More dependencies for the tensorflow-based ID reader:
```
  # sudo dnf install python3-termcolor python3-wheel python3-grpcio \
                     python3-markdown python3-h5py
  # pip3 install --user tensorflow
```


Ubuntu
------

Some stuff from the package manager:
```
  # sudo apt-get install parallel zbar-tools \
                         python3-passlib python3-seaborn python3-pandas \
                         python3-pyqt5 python3-pyqt5.qtsql \
                         python3-peewee python3-pyqrcode python3-png
```
(Ubuntu 18.04 has python3-opencv: older systems may need `pip3`)

These (and others) should work from the package manager but pip pulls them
in anyway, not sure why.
```
  # sudo apt-get install python3-defusedxml python3-jsmin python3-cairosvg
```

Other stuff we get from pip:
```
  # sudo apt-get install python3-pip
  # pip3 install --upgrade --user wsgidav easywebdav2 pymupdf \
                                  weasyprint imutils lapsolver
```
Ubuntu 16.04 also needs:
```
  # pip3 install --user opencv-python peewee pyqrcode pypng

```

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

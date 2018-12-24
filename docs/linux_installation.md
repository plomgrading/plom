<!--
__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__license__ = "GFDL"
 -->
Installing on Popular GNU/Linux Distros
=======================================

Fedora
------

Tested on Fedora 28.  Some stuff from the package manager:

  # dnf install parallel ImageMagick zbar \
                python3-PyMuPDF python3-passlib python3-pypng \
                python3-jsmin python3-defusedxml python3-yaml \
                python3-urllib3 python3-more-itertools \
                python3-seaborn python3-matplotlib-qt5 \


Fedora version too old: python3-peewee, python3-weasyprint (0.22-11 vs 0.42.3-p)
TODO: check Fedora 29 and Rawhide and/or file Fedora bug.

Not yet in fedora: easywebdav2, pyqrcode, wsgidav, cheroot

# pip3 install --user easywebdav2
# pip3 install --user wsgidav
# pip3 install --user cheroot

TODO: fedora has python2-backports-functools_lru_cache, why is there
even such a thing on Python 3?  Pip3 pulls it in for easywebdav2
Probably its a stub package.  Not really our problem as its not a
direct dependency.



Ubuntu
------

Some stuff from the package manager:

# sudo apt-get install python3-pyqt5 python3-passlib parallel zbar-tools python3-pyqt5.qtsql python3-seaborn


These (and others) should work from the package manager but pip pulls them in anyway, not sure why.

# sudo apt-get install python3-defusedxml python3-yaml python3-jsmin python3-urllib3 python3-six

Other stuff we get from pip:

# sudo apt-get install python3-pip
# pip3 install --user peewee
# pip3 install --user wsgidav
# pip3 install --user easywebdav2
# pip3 install --user pymupdf pyqrcode pypng
# pip3 install --user weasyprint

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

<!--
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2022 Colin B. Macdonald"
__copyright__ = "Copyright (C) 2020 Victoria Schuster"
__license__ = "AGPL-3.0-or-later"
 -->

Installing on MacOS
===================

Tested on Catalina 10.15.4. Some stuff from the package manager (Homebrew used in this case) :

If Homebrew is not installed, install Homebrew (not tested):
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
```

A few installations using `brew` from Homebrew:

```
$ brew install libjpeg libjpeg-turbo jpeg-turbo imagemagick zbar \
               libffi jsmin python3 openssl
```

Other stuff we install locally with `pip`:
```
$ pip3 install passlib \
               defusedxml pyYAML urllib3 more-itertools seaborn \
               PyQt5 aiohttp peewee pandas requests-toolbelt toml\
               weasyprint pillow tqdm pytest tex
```

An optional dependency:
```
$ pip3 install passlib jpegtran-cffi
```
(If you have trouble here, `jpegtran-cffi` can be omitted, see
https://gitlab.com/plom/plom/-/merge_requests/960).


More dependencies for the machine-learning-based ID Reader:
```
$ pip3 install termcolor wheel grpcio markdown h5py
$ pip3 install --user imutils lapsolver opencv-python-headless scikit-learn
```
(Also `tensorflow` if using that ID Reader instead).

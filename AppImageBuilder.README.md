# Building PlomClient AppImage

AppImage is a very portable single-file distribution mechanism that end-users can download, make executable and run an app.


## First attempt

First I tried:
```
podman run -it --rm -v ./:/media:z appimage-builder
```
Then `cd /media`
```
appimage-biulder --skip-tests`
```
but this did not work on Fedora 35 (Fontconfig crap, I remember this from PyInstaller, so I assume the appimage-builder container is based on Ubuntu 18.04).


## Success (well, work-in-progress anyway)

```
podman run -it --rm -v ./:/media:z ubuntu:20.04
apt update
apt install -y python3-dev python3-pip
python3 -m pip install --upgrade pip
```
Modified from their install instructions [1]:
TODO: may need `apt-get`
```
DEBIAN_FRONTEND=noninteractive apt install -y python3-pip python3-setuptools patchelf desktop-file-utils libgdk-pixbuf2.0-dev fakeroot strace fuse
```
And some more stuff that wasn't in the instructions:
```
apt install -y gtk-update-icon-cache wget
```
Then again, following [1]:
```
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O /usr/local/bin/appimagetool
chmod +x /usr/local/bin/appimagetool
```

[1] https://appimage-builder.readthedocs.io/en/latest/intro/install.html


```
pip install appimage-builder
```

Build!
```
export APPIMAGE_EXTRACT_AND_RUN=1
appimage-builder --skip-tests
```

Resulting file is currently 88 MiB.


### Tested manually

  * On Ubuntu 18.04, Ubuntu 20.04 and Fedora 35.


### TODO

  * Try `python:3.9` or other image?
  * Replace this file with a Containerfile
  * And/or integrate into our CI
  * Exclude some stuff that ends up in AppDir/usr/bin/
  * Document what bits of our source code to put in: its not just the
    raw git checkout.


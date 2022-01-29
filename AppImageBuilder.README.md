# Building PlomClient AppImage

AppImage is a very portable single-file distribution mechanism that end-users can download, make executable and run an app.


## First attempt

First I tried:
```
podman run -it --rm -v ./:/media:z appimage-builder
```
Then `cd /media` and `appimage-biulder --skip-tests` but this did not work
on Fedora 35 (Fontconfig crap, I remember this from PyInstaller).


## Success (well, work-in-progress anyway)

```
podman run -it --rm -v ./:/media:z ubuntu:20.04
```
Then continue as per the AppImageBuilder.Containerfile.


### Tested manually

  * On Ubuntu 18.04, Ubuntu 20.04 and Fedora 35.


### TODO

  * Try `python:3.9` or other image?
  * And/or integrate into our CI
  * Exclude some stuff that ends up in AppDir/usr/bin/
  * Document what bits of our source code to put in: its not just the
    raw git checkout.
  * WARNING:appimagetool:WARNING: AppStream upstream metadata is missing, please consider creating it
    WARNING:appimagetool:in usr/share/metainfo/org.plomgrading.PlomClient.appdata.xml
  * TODO: version string properly pulled in

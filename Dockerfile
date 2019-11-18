FROM ubuntu:18.04
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata curl
RUN apt-get --no-install-recommends --yes install  \
    parallel zbar-tools cmake \
    python3-passlib python3-seaborn python3-pandas python3-pyqt5 \
    python3-pyqt5.qtsql python3-pyqrcode python3-png python3-pip \
    python3-setuptools python3-wheel imagemagick python3-requests-toolbelt \
    texlive-latex-extra dvipng g++ make python3-dev
RUN pip3 install --upgrade \
    pymupdf weasyprint imutils lapsolver peewee cheroot

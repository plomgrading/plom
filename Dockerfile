FROM ubuntu:18.04
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata curl
RUN apt-get --no-install-recommends --yes install \
    parallel zbar-tools cmake make imagemagick dvipng g++ \
    python3-passlib python3-seaborn python3-pandas python3-pyqt5 \
    python3-pyqt5.qtsql python3-pyqrcode python3-png python3-dev \
    python3-pip python3-setuptools python3-wheel python3-toml \
    python3-requests-toolbelt texlive-latex-extra
RUN pip3 install --upgrade pip
RUN python3 -m pip install --upgrade setuptools
RUN python3 -m pip install --upgrade \
    pymupdf weasyprint imutils lapsolver peewee cheroot aiohttp

FROM ubuntu:19.10
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata
RUN apt-get --no-install-recommends --yes install  \
    zbar-tools cmake make imagemagick g++ \
    python3-passlib python3-pandas python3-pyqt5 \
    python3-pyqt5.qtsql python3-pyqrcode python3-png python3-dev \
    python3-pip python3-setuptools python3-wheel python3-toml \
    texlive-latex-extra dvipng latexmk texlive-fonts-recommended \
    mupdf libmupdf-dev \
    python3-xvfbwrapper python3-tqdm libpango-1.0 libpangocairo-1.0
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade \
    pymupdf weasyprint imutils lapsolver peewee \
    requests requests-toolbelt aiohttp pyzbar pyinstaller

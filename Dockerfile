FROM ubuntu:19.10
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata
RUN apt-get --no-install-recommends --yes install  \
    cmake make imagemagick g++ \
    python3-passlib python3-pandas python3-pyqt5 python3-pytest \
    python3-pyqrcode python3-png python3-dev \
    python3-pip python3-setuptools python3-wheel python3-opencv python3-pil \
    texlive-latex-extra dvipng latexmk texlive-fonts-recommended \
    mupdf libmupdf-dev \
    python3-tqdm libpango-1.0 libpangocairo-1.0 \
    libjpeg-turbo8-dev libturbojpeg0-dev python3-cffi
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade \
    pymupdf weasyprint imutils lapsolver peewee toml \
    requests requests-toolbelt aiohttp pyzbar python3-cffi pyinstaller
RUN pip3 install --upgrade imutils tensorflow lapsolver

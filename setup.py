# SPDX-License-Identifier: FSFAP
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

import os
from setuptools import setup, find_packages
from glob import glob

# TODO: "stop importing things from the local path" or use this workaround:
#sys.path.insert(0, os.dirname(__file__))

# This directory
dir_setup = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(dir_setup, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(dir_setup, "plom", "version.py")) as f:
    # Defines __version__
    exec(f.read())

iconList = []
for fn in glob("plom/client/icons/*.svg"):
    iconList.append(fn)
cursorList = []
for fn in glob("plom/client/cursors/*.png"):
    cursorList.append(fn)

# TODO: CI requires requirements.txt.tempminima synced with mins here:

client_install_requires = ["toml>=0.10.0", "requests", "requests-toolbelt", "PyQt5"]

server_install_requires = [
    "appdirs>=1.4.3",
    "toml>=0.10.0",
    "tqdm",
    "numpy",
    "pandas",
    "passlib",
    "pymupdf>=1.18.5,!=1.18.7",
    "Pillow>=7.0.0",
    "cffi",  # not ours, why doesn't jpegtran-cffi pull this?
    "jpegtran-cffi",
    "weasyprint",
    "aiohttp~=3.7.2",
    "pypng",  # unlisted dep of pyqrcode
    "pyqrcode",
    "pyzbar",
    "peewee>=3.13.3",
    "imutils",
    "opencv-python",
    "scikit-learn>=0.23.1",
    "lapsolver",  # ID reading
    "requests",
    "requests-toolbelt",
]

# Non-Python deps for server
#   - openssl
#   - imagemagick
#   - ghostscript (optional)
#   - latex installation including (Debian/Ubuntu pkg names):
#       texlive-latex-extra dvipng latexmk texlive-fonts-recommended
#   - latex installation including (Fedora pkg names):
#       tex-preview tex-dvipng texlive-scheme-basic tex-xwatermark tex-charter


setup(
    name="plom",
    version=__version__,
    description="Plom is PaperLess Open Marking",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://plomgrading.org",
    author="Andrew Rechnitzer",
    license="AGPLv3+",
    python_requires=">=3.6",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
        "Topic :: Education :: Testing",
    ],
    entry_points={
        "console_scripts": [
            "plom-client=plom.scripts.client:main",
            "plom-demo=plom.scripts.demo:main",
            "plom-hwdemo=plom.scripts.hwdemo:main",
            "plom-init=plom.scripts.plominit:main",
            "plom-build=plom.scripts.build:main",
            "plom-server=plom.scripts.server:main",
            "plom-scan=plom.scripts.scan:main",
            "plom-manager=plom.scripts.manager:main",
            "plom-finish=plom.scripts.finish:main",
            "plom-fake-scribbles=plom.produce.faketools:main",
            "plom-fake-hwscribbles=plom.produce.hwFaker:main",
            "plom-hwscan=plom.scripts.hwscan:main",
        ],
    },
    include_package_data=True,
    data_files=[
        (
            "share/plom",
            [
                "plom/templateTestSpec.toml",
                "plom/produce/digits.json",
                "plom/serverDetails.toml",
                "plom/templateUserList.csv",
                "plom/demoClassList.csv",
                "plom/demoUserList.csv",
                "plom/scan/test_zbar_fails.png",
                "plom/server/target_Q_latex_plom.png",
                "plom/testTemplates/latexTemplate.tex",
                "plom/testTemplates/latexTemplatev2.tex",
                "plom/testTemplates/idBox2.pdf",
                "plom/client/backGrid1.svg",
                "plom/client/backGrid2.png",
            ],
        ),
        ("share/plom/icons", iconList),
        ("share/plom/cursors", cursorList),
        ("share/applications", ["org.plomgrading.PlomClient.desktop"]),
        ("share/metainfo", ["org.plomgrading.PlomClient.metainfo.xml"]),
        ("share/icons/hicolor/128x128/apps/", ["org.plomgrading.PlomClient.png"]),
        # ("share/plom/contrib", glob('contrib/**/*', recursive=True)),
        (
            "share/plom/contrib",
            [
                "contrib/README.txt",
                "contrib/plom-return_codes_to_canvas_csv.py",
                "contrib/plom-write_grades_to_canvas_csv.py",
                "contrib/upload_hw_from_zip_of_jpegs.py",
            ],
        ),
    ],
    install_requires=list(set(client_install_requires + server_install_requires)),
)

# SPDX-License-Identifier: FSFAP
# Copyright (C) 2020-2023 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2022 Elizabeth Xiao
# Copyright (C) 2022 Natalia Accomazzo Scotti
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

import os
from setuptools import setup, find_packages
from glob import glob

# TODO: "stop importing things from the local path" or use this workaround:
# sys.path.insert(0, os.dirname(__file__))

# This directory
dir_setup = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(dir_setup, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(dir_setup, "plom", "version.py")) as f:
    # Defines __version__
    exec(f.read())

# TODO: CI requires requirements.txt.tempminima synced with mins here:

client_install_requires = [
    "appdirs>=1.4.3",
    "arrow>=1.1.1",
    "packaging",
    "passlib",
    "Pillow>=7.0.0",
    "PyQt5",
    "requests",
    "requests-toolbelt",
    "stdiomask>=0.0.6",
    'tomli>=2.0.1 ; python_version<"3.11"',  # until we drop 3.10
    "tomlkit>=0.11.4",
]

server_install_requires = [
    "appdirs>=1.4.3",
    "canvasapi>=2.0.0",
    "exif>=1.2.2",
    "fonttools>=4.37.1",
    "toml>=0.10.0",
    "tqdm",
    "numpy>=1.17.0",
    "pandas>=1.0.0",
    "passlib",
    "pymupdf>=1.21.0",
    "Pillow>=7.0.0",
    "aiohttp>=3.7.2",
    "weasyprint>=52.5",
    "peewee>=3.13.3",
    "PyMySQL>=1.0.2",
    "imutils",
    "opencv-python-headless>=4.4.0.40",
    "scikit-learn>=0.23.1",
    "segno",
    "lapsolver",  # ID reading
    "requests",
    "requests-toolbelt",
    "packaging",
    'importlib_resources>=5.0.0 ; python_version<"3.9"',  # until we drop 3.8
    "stdiomask>=0.0.6",
    "zxing-cpp>=1.4.0",
]
# TODO: optional dependency to enable lossless jpeg rotations
#   "cffi",
#   "jpegtran-cffi",
# TODO: how to get "or"?: https://gitlab.com/plom/plom/-/issues/1570
#   "file-magic || python-magic>=0.4.20",

# Non-Python deps for server
#   - openssl
#   - imagemagick
#   - ghostscript (optional)
#   - latex installation including (Debian/Ubuntu pkg names):
#       texlive-latex-extra dvipng latexmk texlive-fonts-recommended
#   - latex installation including (Fedora pkg names):
#       tex-preview tex-dvipng texlive-scheme-basic tex-charter


setup(
    name="plom",
    version=__version__,  # noqa: F821
    description="Plom is Paperless Open Marking",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://plomgrading.org",
    author="Andrew Rechnitzer",
    license="AGPLv3+",
    python_requires=">=3.7",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
        "Topic :: Education :: Testing",
    ],
    entry_points={
        "console_scripts": [
            "plom-client=plom.client.__main__:main",
            "plom-demo=plom.demo.__main__:main",
            "plom-hwdemo=plom.scripts.hwdemo:main",
            "plom-init=plom.scripts.plominit:main",
            "plom-build=plom.scripts.build_stub:main",
            "plom-create=plom.create.__main__:main",
            "plom-server=plom.server.__main__:main",
            "plom-scan=plom.scan.__main__:main",
            "plom-manager=plom.manager.__main__:main",
            "plom-finish=plom.finish.__main__:main",
            "plom-hwscan=plom.scripts.hwscan:main",
            "plom-solutions=plom.solutions.__main__:main",
        ],
    },
    include_package_data=True,
    data_files=[
        (
            "share/plom",
            [
                "plom/templateTestSpec.toml",
                "plom/templateSolutionSpec.toml",
                "plom/templateUserList.csv",
                "plom/demoClassList.csv",
                "plom/demo_rubrics.toml",
                "plom/create/extra_pages_src.tex",
            ],
        ),
        # TODO: move up from plom
        ("share/plom/testTemplates", glob("plom/testTemplates/**/*", recursive=True)),
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
                "contrib/plom-push-to-canvas.py",
            ],
        ),
    ],
    install_requires=list(set(client_install_requires + server_install_requires)),
)

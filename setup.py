from setuptools import setup, find_packages
from glob import glob

iconList = []
for fn in glob("plom/client/icons/*.svg"):
    iconList.append(fn)
cursorList = []
for fn in glob("plom/client/cursors/*.png"):
    cursorList.append(fn)

setup(
    name="plom",
    version="0.3.90",
    description="Paperless online marking",
    url="https://plom.gitlab.io/plom/",
    author="Andrew Rechnitzer",
    license="AGPL3",
    packages=find_packages(),
    scripts=[
        "plom/scripts/plom-init.py",
        "plom/scripts/plom-scan.py",
        "plom/scripts/plom-build",
        "plom/scripts/plom-client",
        "plom/scripts/plom-manager.py",
        "plom/scripts/plom-server.py",
    ],
    include_package_data=True,
    data_files=[
        ("share/plom", ["plom/templateTestSpec.toml", "plom/serverDetails.toml"]),
        ("share/plom/icons", iconList),
        ("share/plom/cursors", cursorList),
    ],
)

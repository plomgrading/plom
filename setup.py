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
    entry_points={
        "console_scripts": [
            "plom-fake-scribbles=plom.produce.faketools:main",
        ],
    },
    include_package_data=True,
    data_files=[
        (
            "share/plom",
            [
                "plom/templateTestSpec.toml",
                "plom/serverDetails.toml",
                "plom/templateUserList.csv",
                "plom/demoClassList.csv",
                "plom/demoUserList.csv",
                "plom/server/target_Q_latex_plom.png",
            ],
        ),
        ("share/plom/icons", iconList),
        ("share/plom/cursors", cursorList),
    ],
)

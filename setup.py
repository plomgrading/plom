from setuptools import setup, find_packages

setup(
    name="plom",
    version="0.4",
    description="Paperless online marking",
    url="https://plom.gitlab.io/plom/",
    author="Andrew Rechnitzer",
    license="AGPL3",
    packages=find_packages(),
    scripts=["plom/bin/plom-init", "plom/bin/plom-build"],
    include_package_data=True,
    data_files=[("share/plom/resources", ["plom/resources/templateTestSpec.toml"])],
)

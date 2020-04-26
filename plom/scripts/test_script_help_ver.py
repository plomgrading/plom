import subprocess
from plom import __version__

# TODO: -init?
scripts = ["plom-demo", "plom-build", "plom-scan", "plom-finish", "plom-server", "plom-client", "plom-manager"]


def test_scripts_have_hyphen_version():
    for s in scripts:
        assert __version__ in subprocess.check_output([s, "--version"]).decode()


def test_scripts_have_hyphen_help():
    for s in scripts:
        subprocess.check_call([s, "--help"])
        subprocess.check_call([s, "-h"])

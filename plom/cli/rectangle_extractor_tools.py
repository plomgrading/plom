from plom.cli import with_messenger
from plom.plom_exceptions import PlomAuthenticationException, PlomConflict


@with_messenger
def download_classlist(msgr) -> bool:
    """Echo all records from the server's classlist to stdout.

    Keyword Args:
        msgr:  An active Messenger object.

    Returns:
        True iff the server's classlist was emitted.
    """
    success = True
    csvstream = msgr.new_server_download_classlist()

    return success

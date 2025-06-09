from plom.cli import with_messenger
from plom.plom_exceptions import PlomAuthenticationException, PlomConflict


@with_messenger
def extract_rectangle(
    version: int, page_num: int, region: dict[str, float], *, msgr
) -> bool:
    """ """
    return msgr.rectangle_extraction(version, page_num, region)

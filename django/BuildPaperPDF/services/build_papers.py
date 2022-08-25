from plom.create.buildDatabaseAndPapers import build_papers

from django.conf import settings


class BuildPapersService:
    """Use Core Plom to build test-papers."""

    def build_single_paper(index: int, ccs):
        msgr = None
        try:
            msgr = ccs.get_manager_messenger()
            msgr.start()
            msgr.requestAndSaveToken(ccs.manager_username, ccs.get_manager_password())

            build_papers(
                basedir=settings.BASE_DIR,
                indexToMake=index,
                msgr=msgr
            )
        finally:
            if msgr:
                if msgr.token:
                    msgr.clearAuthorisation(ccs.manager_username, ccs.get_manager_password())
                msgr.stop()

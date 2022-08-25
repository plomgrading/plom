from plom.create.buildDatabaseAndPapers import build_papers

from django.conf import settings


class BuildPapersService:
    """Use Core Plom to build test-papers."""
    
    def build_single_paper(messenger):
        build_papers(
            basedir=settings.BASE_DIR,
            indexToMake=1,
            msgr=messenger
        )

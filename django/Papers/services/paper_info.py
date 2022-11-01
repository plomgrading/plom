from django.db import transaction
from Papers.models import Paper, BasePage

import logging

log = logging.getLogger("PaperInfoService")


class PaperInfoService:
    @transaction.atomic
    def how_many_papers_in_database(self):
        """How many papers have been created in the database."""
        return Paper.objects.count()

    @transaction.atomic
    def is_paper_database_populated(self):
        """True if any papers have been created in the DB.

        The database is initially created with empty tables.  Users get added.
        This function still returns False.  Eventually Tests (i.e., "papers")
        get created.  Then this function returns True.
        """
        return Paper.objects.filter().exists()

    def is_this_paper_in_database(self, paper_number):
        """Check if the given paper is in the database."""
        return Paper.objects.filter(paper_number=paper_number).exists()

    @transaction.atomic
    def which_papers_in_database(self):
        """List which papers have been created in the database."""
        return list(Paper.objects.values_list("paper_number", flat=True))

    def page_has_image(self, paper_number, page_number):
        """
        Return True if a page has an Image associated with it.
        """
        paper = Paper.objects.get(paper_number=paper_number)
        page = BasePage.objects.get(paper=paper, page_number=page_number)
        return page.image != None

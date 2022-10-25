from django.db import models

from .image_bundle import Image


class Paper(models.Model):
    """Table to store papers. Each entry corresponds to one (physical)
    test-paper that a student submits. The pages of that test-paper
    are divided into pages - see the AbstractPage class.
    The Paper object does not contain explicit refs to pages, but rather
    the pages will reference the paper (as is usual in a database).

    paper_number (int): The number of the given test-paper.

    """

    paper_number = models.PositiveIntegerField(null=False, unique=True)


class AbstractPage(models.Model):
    """Abstract table to store information about the pages within a given
    group of pages. This table is not used, but rather we define it
    here so that we can use the tables that inherit properties from
    it. Notice that we do not define the group to which this page
    belongs in the abstract class, but instead leave that to the
    derived classes.

    paper (ref to Paper): the test-paper to which this page image belongs
    image (ref to Image): the image
    page_number (int): the position of this page within the test-paper
    """

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, null=True, on_delete=models.SET_NULL)
    page_number = models.PositiveIntegerField(null=False)

    class Meta:
        abstract = True


class DNMPage(AbstractPage):
    """
    Table to store information about the pages in DoNotMark groups.
    """

    pass


class IDPage(AbstractPage):
    """Table to store information about the pages in ID groups.

    Notice that at present IDGroups should only contain a single page
    so this IDPages should always have page-number = 1.

    """

    pass


class QuestionPage(AbstractPage):
    """Table to store information about the pages in Question groups.

    question_number (int): the question that this page belongs to.
    question_version (int): the version of the question.
    """

    question_number = models.PositiveIntegerField(null=False, default=0)
    question_version = models.PositiveIntegerField(null=False, default=1)

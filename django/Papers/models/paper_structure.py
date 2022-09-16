from django.db import models

from .image_bundle import Image


class Paper(models.Model):
    """Table to store papers. Each entry corresponds to one (physical)
    test-paper that a student submits. The pages of that test-paper
    are divided into groups of pages - see the AbstractGroup class.
    The Paper object does not contain explicit refs to groups, but rather
    the groups will reference the paper (as is usual in a database).

    paper_number (int): The number of the given test-paper.

    """

    paper_number = models.PositiveIntegerField(null=False, unique=True)


# ---------------------------------

# A given paper consists of groups of pages. There are 3 types of
# groups and so 3 types of pages to go with them.

# We define an abstract group class from which the actual groups are
# defined - namely IDGroup, DNMGroup and QuestionGroup.

# We also define an abstract page class from which the different page
# types are defined, IDPage, DNMPage and QuestionPage

# NOTE - have changed format of the group - gid - for django.

# ---------------------------------


class AbstractGroup(models.Model):
    """Abstract table to store information about a group of pages within a
    given test-paper This table is not used, but rather we define it
    here so that we can use the tables that inherit properties from
    it.

    Notice that this group table does not contain explicit refs to pages,
    rather the pages will reference the group (as is the standard way to
    define one-to-many links in a database).

    paper (ref to Paper object): which test-paper the group of pages belongs to
    gid (str): an id-string for the group. Is of the from
        * "0123i" = the group of id-pages for paper 0123
        * "0123d" = the group of do-not-mark pages for paper 0123
        * "0123q2" = the group of question-pages for paper 0123, for
            question 2.

    expected_number_pages (int): the expected number of pages in this
        group as indicated by the test specification.
    integrity_check (uuid): a uuid that is assigned each time the pages
        underlying the group is changed. Used to check whether the task
        associated with the group is outdated or not.
    complete (bool): Set to true when all the required pages are present,
        else false.

    """

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    gid = models.CharField(null=False, max_length=16)

    expected_number_pages = models.PositiveIntegerField(null=False, default=0)
    integrity_check = models.UUIDField(null=True)
    complete = models.BooleanField(null=False, default=False)

    class Meta:
        abstract = True


class AbstractPage(models.Model):
    """Abstract table to store information about the pages within a given
    group of pages. This table is not used, but rather we define it
    here so that we can use the tables that inherit properties from
    it. Notice that we do not define the group to which this page
    belongs in the abstract class, but instead leave that to the
    derived classes.

    paper (ref to Paper): the test-paper to which this page image belongs
    image (ref to Image): the image
    page_number (int): the position of this page **within** the group of
        pages. For example, if the Q3 contains (actual on paper) pages
        7,8,9, then these will have page-numbers 1,2,3. Then any extra
        pages that a student might use will have numbers 4,5,...

    """

    # we don't have a group ref instead leave that to the descendants
    # so that, say, an IDPage has a ref to the IDGroup.
    # group = models.ForeignKey(Group, null=False, on_delete=models.CASCADE)

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    page_number = models.PositiveIntegerField(null=False)

    class Meta:
        abstract = True


# ---------------------------------

# Now define the concrete groups from the above abstract group

# ---------------------------------


class DNMGroup(AbstractGroup):
    """Table derived from AbstractGroup for holding pages of Do-not-mark
    group of pages.  Has no additional properties.

    Notice that for many test-specifications there will be no DNM-pages,
    and in that case expected_number_pages will be set to 0.

    """

    pass


class IDGroup(AbstractGroup):
    """Table derived from AbstractGroup for holding pages of ID-group of pages.

    Notice that at present this should be only a single page (but was
    different previously and could change in the future), and so
    expected_number_pages should be set to 1.

    Has no additional properties.

    """

    pass


class QuestionGroup(AbstractGroup):
    """Table derived from AbstractGroup for holding pages of
    question-group of pages. Requires additional properties.

    Notice that a question group will typically contain the
    expected_number_pages, however there are circumstances in which it
    can contain more (eg student submits several extra pages for this
    question), or fewer (eg student-submitted homework).


    question (int): The number of the question (this will often line
        up with the question-label, but not always).
    label (str): The label of this question (this will often line up
        with the question number, but not always).
    version (int): The version of the question.
    max_mark (int): The maximum possible mark for this question.
    tags (refs to QuestionTagLink): Links to user-assigned tags for
        this question of this paper. The many-to-many link is
        constructed by entries in the QuestionTagLink table.

    """

    question = models.PositiveIntegerField(null=False)
    label = models.TextField(null=False)
    version = models.PositiveIntegerField(null=False)
    max_mark = models.PositiveIntegerField(null=False)

    # TODO - add tags
    # tags = models.ManyToManyField(Tag, through="QuestionTagLink")


# ---------------------------------

# Now define the concrete page from the above abstract page

# ---------------------------------


class DNMPage(AbstractPage):
    """Table to store information about the pages in DoNotMark groups.

    dnmgroup (ref to DNMGroup): the dnm group to which the page
        belongs.

    """

    dnmgroup = models.ForeignKey(DNMGroup, null=False, on_delete=models.CASCADE)


class IDPage(AbstractPage):
    """Table to store information about the pages in ID groups.

    Notice that at present IDGroups should only contain a single page
    so this IDPages should always have page-number = 1.

    idgroup (ref to IDGroup): the id-group to which the page belongs.

    """

    idgroup = models.ForeignKey(IDGroup, null=False, on_delete=models.CASCADE)


class QuestionPage(AbstractPage):
    """Table to store information about the pages in Question groups.


    questiongroup (ref to QGroup): the question-group to which the
        page belongs.

    """

    questiongroup = models.ForeignKey(
        QuestionGroup, null=False, on_delete=models.CASCADE
    )

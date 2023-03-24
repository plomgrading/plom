# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer

from django.db import models
from polymorphic.models import PolymorphicModel

from .image_bundle import Image


class Paper(models.Model):
    """Table to store papers. Each entry corresponds to one (physical)
    test-paper that a student submits. The pages of that test-paper
    are divided into pages - see the BasePage class.
    The Paper object does not contain explicit refs to pages, but rather
    the pages will reference the paper (as is usual in a database).

    paper_number (int): The number of the given test-paper.

    """

    paper_number = models.PositiveIntegerField(null=False, unique=True)


class BasePage(PolymorphicModel):
    """Base table to store information about the pages within a given
    group of pages. We then use polymorphism to define derived classes
    of pages: IDPage, DNMPage, QuestionPage. The base class should
    contain all info common to these classes. Searching on this base
    class allows us to search over all pages, while searching on a
    derived class only searches over those page types.

    paper (ref to Paper): the test-paper to which this page image belongs
    image (ref to Image): the image
    page_number (int): the position of this page within the test-paper
    _version (int): the version of this paper/page as determined by
        the qvmap. Note that this field is temporary until we start
        dealing with extra-pages

    """

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, null=True, on_delete=models.SET_NULL)
    page_number = models.PositiveIntegerField(null=False)
    # temporarily include the version here until we work out how to deal with
    # extra-pages
    _version = models.PositiveIntegerField(null=False)


class DNMPage(BasePage):
    """Table to store information about the pages in DoNotMark
    groups. At present we construct DNM pages so that they always have
    _version=1. This may change in the future."""

    pass


class IDPage(BasePage):
    """Table to store information about the pages in ID groups.

    Notice that at present IDGroups should only contain a single page
    so this IDPages should always have page-number = 1.  Also note
    that at present we construct ID pages so that they always have
    _version=1. This may change in the future.

    """

    pass


class QuestionPage(BasePage):
    """Table to store information about the pages in Question groups.

    question_number (int): the question that this page belongs to.
    question_version (int): the version of the question.
    """

    question_number = models.PositiveIntegerField(null=False, default=0)
    question_version = models.PositiveIntegerField(null=False, default=1)

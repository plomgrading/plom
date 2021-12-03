# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald
# Copyright (C) 2021 Nicholas J H Lai

import peewee as pw

plomdb = pw.SqliteDatabase(None)


class BaseModel(pw.Model):
    class Meta:
        database = plomdb


class User(BaseModel):
    name = pw.CharField(unique=True)
    enabled = pw.BooleanField(default=True)
    password = pw.CharField(null=True)  # hash of password for comparison
    token = pw.CharField(null=True)  # authentication token
    last_activity = pw.DateTimeField(null=True)
    last_action = pw.CharField(null=True)


class Bundle(BaseModel):
    name = pw.CharField(unique=True, null=True)  # unique names please
    md5sum = pw.CharField(null=True)  # to check for duplications


class Image(BaseModel):
    bundle = pw.ForeignKeyField(Bundle, backref="images")
    original_name = pw.CharField(null=True)  # can be empty.
    # the order of the image within its bundle
    bundle_order = pw.IntegerField(null=True)
    file_name = pw.CharField(null=True)
    md5sum = pw.CharField(null=True)  # to check for duplications


class Test(BaseModel):
    test_number = pw.IntegerField(primary_key=True, unique=True)
    # some state pw.Bools
    used = pw.BooleanField(default=False)
    scanned = pw.BooleanField(default=False)
    identified = pw.BooleanField(default=False)
    marked = pw.BooleanField(default=False)


class Group(BaseModel):
    test = pw.ForeignKeyField(Test, backref="groups")
    gid = pw.CharField(unique=True)  # must be unique
    group_type = pw.CharField()  # to distinguish between ID, DNM, and Mark groups
    queue_position = pw.IntegerField(unique=True, null=False)
    scanned = pw.BooleanField(default=False)  # should get all its tpages


class IDGroup(BaseModel):
    test = pw.ForeignKeyField(Test, backref="idgroups")
    group = pw.ForeignKeyField(Group, backref="idgroups")
    student_id = pw.CharField(unique=True, null=True)
    student_name = pw.CharField(null=True)
    user = pw.ForeignKeyField(User, backref="idgroups", null=True)
    status = pw.CharField(default="")
    time = pw.DateTimeField(null=True)
    identified = pw.BooleanField(default=False)


class DNMGroup(BaseModel):
    test = pw.ForeignKeyField(Test, backref="dnmgroups")
    group = pw.ForeignKeyField(Group, backref="dnmgroups")


class QGroup(BaseModel):
    test = pw.ForeignKeyField(Test, backref="qgroups")
    group = pw.ForeignKeyField(Group, backref="qgroups")
    question = pw.IntegerField(null=False)
    version = pw.IntegerField(null=False, default=1)
    user = pw.ForeignKeyField(User, backref="qgroups", null=True)
    status = pw.CharField(default="")
    time = pw.DateTimeField(null=True)
    marked = pw.BooleanField(default=False)
    # fullmark = pw.IntegerField(null=False)


class TPage(BaseModel):  # a test page that knows its tpgv
    test = pw.ForeignKeyField(Test, backref="tpages")
    page_number = pw.IntegerField(null=False)
    version = pw.IntegerField(default=1)
    group = pw.ForeignKeyField(Group, backref="tpages")
    image = pw.ForeignKeyField(Image, backref="tpages", null=True)
    scanned = pw.BooleanField(default=False)  # we should get all of them
    # note - Do not delete - rather set scanned=False


class HWPage(BaseModel):  # a hw page that knows its tgv, but not p.
    test = pw.ForeignKeyField(Test, backref="hwpages")
    group = pw.ForeignKeyField(Group, backref="hwpages")
    order = pw.IntegerField(null=False)
    version = pw.IntegerField(default=1)  # infer from group
    image = pw.ForeignKeyField(Image, backref="hwpages")


# an extra page that knows its tgv, but not p. - essentially same as hwpages.
class EXPage(BaseModel):
    test = pw.ForeignKeyField(Test, backref="expages")
    group = pw.ForeignKeyField(Group, backref="expages")
    order = pw.IntegerField(null=False)
    version = pw.IntegerField(default=1)  # infer from group
    image = pw.ForeignKeyField(Image, backref="expages")


# still needs work - maybe some bundle object with unique key.
class UnknownPage(BaseModel):
    image = pw.ForeignKeyField(Image, backref="upages", null=True)
    order = pw.IntegerField(null=False)  # order within the upload.


class CollidingPage(BaseModel):
    tpage = pw.ForeignKeyField(TPage, backref="collisions")
    image = pw.ForeignKeyField(Image, backref="collisions")


class DiscardedPage(BaseModel):
    image = pw.ForeignKeyField(Image, backref="discards")
    reason = pw.CharField(null=True)


class IDPage(BaseModel):
    # even though there is only one, for simplicity
    # this is a many-to-one mapping by this backref
    idgroup = pw.ForeignKeyField(IDGroup, backref="idpages")
    image = pw.ForeignKeyField(Image, backref="idpages")
    order = pw.IntegerField(null=False)


class DNMPage(BaseModel):
    dnmgroup = pw.ForeignKeyField(DNMGroup, backref="dnmpages")
    image = pw.ForeignKeyField(Image, backref="dnmpages")
    order = pw.IntegerField(null=False)


class AImage(BaseModel):  # a class for containing annotation-images
    file_name = pw.CharField(null=True)
    md5sum = pw.CharField(null=True)  # to check for duplications


class Annotation(BaseModel):
    qgroup = pw.ForeignKeyField(QGroup, backref="annotations")
    user = pw.ForeignKeyField(User, backref="annotations", null=True)
    aimage = pw.ForeignKeyField(AImage, backref="annotations", null=True)
    edition = pw.IntegerField(null=True)
    integrity_check = pw.CharField(null=True)  # random uuid
    # add this for when we update underlying pages of
    # a test
    outdated = pw.BooleanField(default=False)
    #
    # we need to order the annotations - want the latest.
    plom_file = pw.CharField(null=True)
    mark = pw.IntegerField(null=True)
    marking_time = pw.IntegerField(null=True)
    time = pw.DateTimeField(null=True)


class APage(BaseModel):
    annotation = pw.ForeignKeyField(Annotation, backref="apages")
    image = pw.ForeignKeyField(Image, backref="apages")
    order = pw.IntegerField(null=False)


class Rubric(BaseModel):
    # unique key - user-generated have 12 digits, HAL uses 1XXX.
    key = pw.CharField(unique=True, null=False)
    kind = pw.CharField(null=False)  # abs, neut, delt, relative
    delta = pw.CharField(null=False)
    text = pw.CharField(null=False)
    question = pw.IntegerField(null=False)
    user = pw.ForeignKeyField(User, backref="rubrics", null=False)
    revision = pw.IntegerField(null=False, default=0)
    count = pw.IntegerField(null=False, default=0)
    creationTime = pw.DateTimeField(null=False)
    modificationTime = pw.DateTimeField(null=False)
    tags = pw.CharField(default="")
    meta = pw.CharField(default="")


class ARLink(BaseModel):
    annotation = pw.ForeignKeyField(Annotation, backref="arlinks")
    rubric = pw.ForeignKeyField(Rubric, backref="arlinks")


class Tag(BaseModel):
    # unique key - user-generated have 10 digits
    key = pw.CharField(unique=True, null=False)
    text = pw.CharField(null=False)
    creationTime = pw.DateTimeField(null=False)
    user = pw.ForeignKeyField(User, backref="tags", null=False)


class QuestionTagLink(BaseModel):
    qgroup = pw.ForeignKeyField(QGroup, backref="questiontaglinks")
    tag = pw.ForeignKeyField(Tag, backref="questiontaglinks")
    user = pw.ForeignKeyField(User, backref="questiontaglinks", null=False)

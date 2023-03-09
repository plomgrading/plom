# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Andrew Rechnitzer
# Copyright (C) 2021-2023 Colin B. Macdonald
# Copyright (C) 2021 Nicholas J H Lai
# Copyright (C) 2022 Joey Shi
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2022 Brennen Chiu

import json

import peewee as pw


database_proxy = pw.Proxy()


class BaseModel(pw.Model):
    class Meta:
        database = database_proxy


class User(BaseModel):
    # TODO - should this be short - if so we need to check length elsewhere in code.
    name = pw.CharField(unique=True, max_length=1000)
    enabled = pw.BooleanField(default=True)
    password = pw.CharField(null=True)  # hash of password for comparison - fixed length
    token = pw.CharField(null=True)  # authentication token - fixed length
    last_activity = pw.DateTimeField(null=False)
    last_action = pw.CharField(null=False)  # System generated string, not long


class Bundle(BaseModel):
    name = pw.TextField(unique=True, null=True)  # unique names please - can be long
    md5sum = pw.CharField(null=True)  # to check for duplications - fixed length


class Image(BaseModel):
    bundle = pw.ForeignKeyField(Bundle, backref="images")
    original_name = pw.TextField(null=True)  # can be empty - can be long
    # the order of the image within its bundle
    bundle_order = pw.IntegerField(null=True)
    file_name = pw.TextField(null=True)  # can be long
    md5sum = pw.CharField(null=True)  # to check for duplications - fixed length
    rotation = pw.IntegerField(null=False, default=0)


class Test(BaseModel):
    test_number = pw.IntegerField(primary_key=True, unique=True)
    # some state pw.Bools
    used = pw.BooleanField(default=False)
    scanned = pw.BooleanField(default=False)
    identified = pw.BooleanField(default=False)
    marked = pw.BooleanField(default=False)


class Group(BaseModel):
    test = pw.ForeignKeyField(Test, backref="groups")
    gid = pw.CharField(unique=True)  # must be unique - is short
    # short string to distinguish between ID, DNM, and Mark groups
    group_type = pw.CharField()
    queue_position = pw.IntegerField(unique=True, null=False)
    scanned = pw.BooleanField(default=False)  # should get all its tpages


class IDPrediction(BaseModel):
    test = pw.ForeignKeyField(Test, backref="idpredictions")
    student_id = pw.CharField(null=True)  # short, no arbitrary length ids
    user = pw.ForeignKeyField(User, backref="idpredictions", null=True)
    predictor = pw.CharField(null=False)  # is short - system generated.
    certainty = pw.DoubleField(null=False, default=0.0)


class IDGroup(BaseModel):
    test = pw.ForeignKeyField(Test, backref="idgroups")
    group = pw.ForeignKeyField(Group, backref="idgroups")
    student_id = pw.CharField(unique=True, null=True)  # short, no arbitrary length ids
    student_name = pw.TextField(null=True)
    user = pw.ForeignKeyField(User, backref="idgroups", null=True)
    status = pw.CharField(default="")  # system generated - is short
    time = pw.DateTimeField(null=False)
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
    status = pw.CharField(default="")  # system generated - is short
    time = pw.DateTimeField(null=False)
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
    reason = pw.TextField(null=True)  # Might be long


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
    file_name = pw.TextField(null=True)  # might be long
    md5sum = pw.CharField(null=True)  # to check for duplications - is fixed length


class Annotation(BaseModel):
    qgroup = pw.ForeignKeyField(QGroup, backref="annotations")
    user = pw.ForeignKeyField(User, backref="annotations", null=True)
    aimage = pw.ForeignKeyField(AImage, backref="annotations", null=True)
    edition = pw.IntegerField(null=True)
    integrity_check = pw.CharField(null=True)  # random uuid - is fixed length
    # add this for when we update underlying pages of
    # a test
    outdated = pw.BooleanField(default=False)
    #
    # we need to order the annotations - want the latest.
    plom_json = pw.TextField(null=True)
    mark = pw.IntegerField(null=True)
    marking_time = pw.IntegerField(null=True)
    time = pw.DateTimeField(null=False)


class APage(BaseModel):
    annotation = pw.ForeignKeyField(Annotation, backref="apages")
    image = pw.ForeignKeyField(Image, backref="apages")
    order = pw.IntegerField(null=False)


class Rubric(BaseModel):
    # unique key - user-generated have 12 digits
    key = pw.CharField(unique=True, null=False)  # system generated + short
    kind = pw.CharField(null=False)  # short code for what kind of rubric
    display_delta = pw.CharField(null=False)  # is short
    # Note: designing for "value / out_of" absolute rubrics
    #   - value is also used for relative rubrics
    value = pw.IntegerField(null=False)
    out_of = pw.IntegerField(null=False)
    text = pw.TextField(null=False)  # can be long
    question = pw.IntegerField(null=False)
    # versions is a list of integers, stored in json field
    #   "[]": all versions
    #   "[1, 3]": versions 1 and 3 only
    versions = pw.TextField(null=False, default=json.dumps([]))
    parameters = pw.TextField(null=False, default=json.dumps([]))
    user = pw.ForeignKeyField(User, backref="rubrics", null=False)
    revision = pw.IntegerField(null=False, default=0)
    count = pw.IntegerField(null=False, default=0)
    creationTime = pw.DateTimeField(null=False)
    modificationTime = pw.DateTimeField(null=False)
    tags = pw.TextField(default="")  # can be long
    meta = pw.TextField(default="")  # can be long


class ARLink(BaseModel):
    annotation = pw.ForeignKeyField(Annotation, backref="arlinks")
    rubric = pw.ForeignKeyField(Rubric, backref="arlinks")


class Tag(BaseModel):
    # unique key - user-generated have 10 digits
    key = pw.CharField(unique=True, null=False)  # is short
    text = pw.TextField(null=False)  # can be long
    creationTime = pw.DateTimeField(null=False)
    user = pw.ForeignKeyField(User, backref="tags", null=False)


class QuestionTagLink(BaseModel):
    qgroup = pw.ForeignKeyField(QGroup, backref="questiontaglinks")
    tag = pw.ForeignKeyField(Tag, backref="questiontaglinks")
    user = pw.ForeignKeyField(User, backref="questiontaglinks", null=False)

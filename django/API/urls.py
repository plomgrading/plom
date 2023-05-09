# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from django.urls import include, path

from API.routes import (
    MarkURLPatterns,
    IdURLPatterns,
    PagedataPatterns,
    AnnotationPatterns,
    AnnotationImagePatterns,
    MiscURLPatterns,
)

"""
Handle URL patterns for the plom-client / server API.
See docs for including other URLconfs:
https://docs.djangoproject.com/en/4.2/topics/http/urls/#including-other-urlconfs

Note: The URL Patterns classes are made in order to seamlessly split up urls.py
across multiple files. In the future, once we're able to start changing the design
of the plom-client URLS, we ought to transition to using Django REST Framework
routers: https://www.django-rest-framework.org/api-guide/routers/
"""


urlpatterns = [
    path("", include(MiscURLPatterns.patterns)),
    path(MarkURLPatterns.prefix, include(MarkURLPatterns.patterns)),
    path(IdURLPatterns.prefix, include(IdURLPatterns.patterns)),
    path(PagedataPatterns.prefix, include(PagedataPatterns.patterns)),
    path(AnnotationPatterns.prefix, include(AnnotationPatterns.patterns)),
    path(AnnotationImagePatterns.prefix, include(AnnotationImagePatterns.patterns)),
]

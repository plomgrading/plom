# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from rest_framework.viewsets import ModelViewSet
from rest_framework.authentication import BasicAuthentication

from ...permissions import IsManagerReadOnly


class ManagerReadOnlyViewSet(ModelViewSet):
    """Base viewset for exposing DRF-generated endpoints to models.

    Only the Manager user has read access, and no user has write access.
    """

    authentication_classes = [BasicAuthentication]
    permission_classes = [IsManagerReadOnly]

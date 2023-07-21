# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.contrib.auth.models import User
from django.db import transaction
from typing import Dict, List

from Mark.models import Annotation

class UserInfoServices:
    """Functions for User Info HTML page."""

    @transaction.atomic
    def annotation_exists(self) -> bool:
        """Return True if there are any annotations in the database.
        
        Returns:
            bool : True if there are annotations or 
                False if there aren't any
        """
        return Annotation.objects.exists()
    
    @transaction.atomic
    def get_total_annotations_based_on_user(self) -> Dict[User, list]:
        """Get all the annotations based on user.

        Returns:
            Dict: A dictionary of all annotations(Value) corresponding with the markers(key).
        
        Raises:
            Not expected to raise any exceptions.
        """
        markers = User.objects.filter(groups__name="marker")
        marker_ids = [marker.id for marker in markers]
        annotations = Annotation.objects.filter(user_id__in=marker_ids)

        annotation_data: Dict[User, List] = {marker: [] for marker in markers}

        for annotation in annotations:
            annotation_data[annotation.user].append(annotation)
        
        return annotation_data

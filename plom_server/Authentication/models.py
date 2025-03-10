# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023, 2025 Colin B. Macdonald

from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(max_length=100)
    signup_confirmation = models.BooleanField(default=False)

    def __str__(self):
        """Conversion to a string."""
        return self.user.username


@receiver(post_save, sender=User)
def update_profile_signal(sender, instance: User, created: bool, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer
#
# But this codes seems to have originally come from
#    https://gist.github.com/un33k/2913897
# (or perhaps that is just a fork).

from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin

# Online Threshold: If the user was logged out for 30 minutes after 2 hours inactivity,
#                   The user will become inactive status
# Online Max: Maximum markers and scanners in total allowed to be active together
ONLINE_THRESHOLD = getattr(settings, "ONLINE_THRESHOLD", 60 * 30)
ONLINE_MAX = getattr(settings, "ONLINE_MAX", 60)


def get_online_now(self):
    return User.objects.filter(id__in=self.online_now_ids or [])


class OnlineNowMiddleware(MiddlewareMixin):
    """Maintains a list of users who have interacted with the website recently.

    Their user IDs are available as ``online_now_ids`` on the request object,
    and their corresponding users are available (lazily) as the
    ``online_now`` property on the request object.
    """

    def process_request(self, request):
        # First get the index
        uids = cache.get("online-now", [])

        # Perform the multiget on the individual online uid keys
        online_keys = ["online-%s" % (u,) for u in uids]
        fresh = cache.get_many(online_keys).keys()
        online_now_ids = [int(k.replace("online-", "")) for k in fresh]

        # If the user is authenticated, add their id to the list
        if request.user.is_authenticated:
            uid = request.user.id
            # If their uid is already in the list, we want to bump it
            # to the top, so we remove the earlier entry.
            if uid in online_now_ids:
                online_now_ids.remove(uid)
            online_now_ids.append(uid)
            # If the total number of online users is greater than 60,
            # we will force to logout some users
            if len(online_now_ids) > ONLINE_MAX:
                del online_now_ids[0]

        # Attach our modifications to the request object
        request.__class__.online_now_ids = online_now_ids
        request.__class__.online_now = property(get_online_now)

        # Set the new cache
        cache.set("online-%s" % (request.user.pk,), True, ONLINE_THRESHOLD)
        cache.set("online-now", online_now_ids, ONLINE_THRESHOLD)

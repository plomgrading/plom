# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Chris Jin
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024, 2026 Aidan Murphy
#
# But this codes seems to have originally come from
#    https://gist.github.com/un33k/2913897
# (or perhaps that is just a fork).

from django.core.cache import cache
from django.conf import settings


class OnlineNowMiddleware:
    """Maintains a list of users who have interacted with the website recently.

    Rather than posting to the db every time a user makes a request,
    it is cached for fast recall.
    Using the cache means the list isn't reliable if the server is multithreaded.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        self.process_request(request)

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_request(self, request):
        """Update the list of online users.

        The list is ordered according to who has spen the most time idle.
        """
        uids = cache.get("online-now", [])

        # Perform the multiget on the individual online uid keys
        online_keys = ["online-%s" % (u,) for u in uids]
        fresh = cache.get_many(online_keys).keys()
        online_now_ids = [int(k.replace("online-", "")) for k in fresh]

        if request.user.is_authenticated:
            uid = request.user.id
            # order list by recency
            if uid in online_now_ids:
                online_now_ids.remove(uid)
            online_now_ids.append(uid)
            # long lists cause performance issues
            if len(online_now_ids) > settings.ONLINE_MAX:
                del online_now_ids[0]

        # Set the new cache
        cache.set("online-%s" % (request.user.pk,), True, settings.ONLINE_THRESHOLD)
        cache.set(
            "online-now", online_now_ids, settings.ONLINE_THRESHOLD
        )  # race condition

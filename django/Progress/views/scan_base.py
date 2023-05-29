# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from Base.base_group_views import ManagerRequiredView

from Progress.services import ManageScanService


class BaseScanProgressPage(ManagerRequiredView):
    """
    Base view for each of the "tabs" in the scanning progress card.
    """

    def build_context(self, page_name):
        """
        page_name (str): name of the current page, for coloring in the active tab
        """

        mss = ManageScanService()
        context = super().build_context()
        context.update(
            {
                "curr_page": page_name,
                "n_colliding": 0,  # mss.get_n_colliding_pages(),
                "n_error": 0,  # mss.get_n_error_image(),
                "n_discarded": 0,  # mss.get_n_discarded_pages(),
                "n_error": 0,  # mss.get_n_error_image(),
            }
        )

        return context

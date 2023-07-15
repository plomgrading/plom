# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from Base.base_group_views import ManagerRequiredView


class BaseScanProgressPage(ManagerRequiredView):
    """Base view for each of the "tabs" in the pushed progress card."""

    def build_context(self, page_name):
        """Build the context for the base pushed progress.

        Arguments:
            page_name (str): name of the current page, for coloring in the active tab
        """
        context = super().build_context()
        context.update(
            {
                "curr_page": page_name,
            }
        )

        return context

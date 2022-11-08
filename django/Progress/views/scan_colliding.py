from django.shortcuts import render
from django.http import FileResponse, Http404
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User

from Base.base_group_views import ManagerRequiredView

from Progress.views import BaseScanProgressPage
from Progress.services import ManageScanService


class ScanColliding(BaseScanProgressPage):
    """
    View and manage colliding pages.
    """

    def get(self, request):
        context = self.build_context("colliding")
        mss = ManageScanService()

        context.update(
            {
                "colliding_pages": mss.get_colliding_pages_list(),
            }
        )
        return render(request, "Progress/scan_collide.html", context)


class CollidingPagesModal(ManagerRequiredView):
    """
    Display an original page next to a colliding page, and provide
    actions for resolving the collision.
    """

    def get(self, request, test_paper, index, colliding_hash):
        context = self.build_context()

        context.update(
            {
                "test_paper": test_paper,
                "index": index,
                "colliding_hash": colliding_hash,
            }
        )

        return render(request, "Progress/fragments/scan_collision_modal.html", context)


class CollisionPageImage(ManagerRequiredView):
    """
    Display the collision page-image.
    """

    def get(self, request, colliding_hash):
        mss = ManageScanService()
        colliding_image = mss.get_colliding_image(colliding_hash)

        with open(str(colliding_image.file_name), "rb") as f:
            paper_number = colliding_image.paper_number
            page_number = colliding_image.page_number
            image_file = SimpleUploadedFile(
                f"{paper_number:04}_page{page_number}_colliding.png",
                f.read(),
                content_type="image/png",
            )
        return FileResponse(image_file)

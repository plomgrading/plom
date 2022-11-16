from django.contrib import admin

from Papers.models.paper_structure import (
    Paper,
    IDPage,
    DNMPage,
    QuestionPage,
)
from Papers.models.specifications import Specification
from Papers.models.background_tasks import CreatePaperTask, CreateImageTask
from Papers.models.image_bundle import (
    Image,
    CollidingImage,
    DiscardedImage,
)

admin.site.register(Paper)
admin.site.register(Specification)
admin.site.register(IDPage)
admin.site.register(DNMPage)
admin.site.register(QuestionPage)
admin.site.register(CreatePaperTask)
admin.site.register(CreateImageTask)
admin.site.register(Image)
admin.site.register(CollidingImage)
admin.site.register(DiscardedImage)

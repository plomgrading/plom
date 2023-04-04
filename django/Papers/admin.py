from django.contrib import admin

from Papers.models.paper_structure import (
    Paper,
    MobilePage,
    FixedPage,
    IDPage,
    DNMPage,
    QuestionPage,
)
from Papers.models.specifications import Specification
from Papers.models.background_tasks import CreatePaperTask, CreateImageTask
from Papers.models.image_bundle import (
    Image,
    DImage,
    Bundle
)

admin.site.register(Paper)
admin.site.register(Specification)
admin.site.register(MobilePage)
admin.site.register(FixedPage)
admin.site.register(IDPage)
admin.site.register(DNMPage)
admin.site.register(QuestionPage)
admin.site.register(CreatePaperTask)
admin.site.register(CreateImageTask)
admin.site.register(Bundle)
admin.site.register(Image)
admin.site.register(DImage)

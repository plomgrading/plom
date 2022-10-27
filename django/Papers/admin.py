from django.contrib import admin

from Papers.models.paper_structure import (
    Paper,
    IDPage,
    DNMPage,
    QuestionPage,
)
from Papers.models.specifications import Specification
from Papers.models.background_tasks import CreatePaperTask

admin.site.register(Paper)
admin.site.register(Specification)
admin.site.register(IDPage)
admin.site.register(DNMPage)
admin.site.register(QuestionPage)
admin.site.register(CreatePaperTask)

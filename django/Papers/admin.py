from django.contrib import admin

from Papers.models.paper_structure import (
    Paper,
    IDGroup,
    DNMGroup,
    QuestionGroup,
)
from Papers.models.specifications import Specification
from Papers.models.background_tasks import CreatePaperTask

admin.site.register(Paper)
admin.site.register(IDGroup)
admin.site.register(DNMGroup)
admin.site.register(QuestionGroup)
admin.site.register(Specification)
admin.site.register(CreatePaperTask)

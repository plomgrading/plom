from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.ReferencePDF)
admin.site.register(models.TestSpecInfo)
admin.site.register(models.TestSpecQuestion)
admin.site.register(models.StagingSpecification)

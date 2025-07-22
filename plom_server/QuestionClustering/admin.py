from django.contrib import admin

from .models import QVCluster, QVClusterLink

# This makes models appear in the admin interface
admin.site.register(QVCluster)
admin.site.register(QVClusterLink)

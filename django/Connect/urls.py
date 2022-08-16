from django.urls import path
from Connect.views import ConnectServerManagerView

urlpatterns = [
    path('', ConnectServerManagerView.as_view(), name='connect_manager'),
]
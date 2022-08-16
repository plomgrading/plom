from django.urls import path
from Connect.views import ConnectServerManagerView, AttemptCoreConnectionView

urlpatterns = [
    path('', ConnectServerManagerView.as_view(), name='connect_manager'),
    path('initial/', AttemptCoreConnectionView.as_view(), name='attempt_core_connection'),
]
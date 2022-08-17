from django.urls import path
from Connect.views import (
    ConnectServerManagerView, 
    AttemptCoreConnectionView, 
    AttemptCoreManagerLoginView
    )

urlpatterns = [
    path('', ConnectServerManagerView.as_view(), name='connect_manager'),
    path('initial/', AttemptCoreConnectionView.as_view(), name='attempt_core_connection'),
    path('signup_manager/', AttemptCoreManagerLoginView.as_view(), name='attempt_manager_signup')
]
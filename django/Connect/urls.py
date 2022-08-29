from django.urls import path
from Connect.views import (
    ConnectServerManagerView, 
    AttemptCoreConnectionView, 
    ForgetCoreConnectionView,
    AttemptCoreManagerLoginView,
    ForgetCoreManagerLoginView,
    ConnectSendInfoToCoreView,
    SendTestSpecToCoreView,
    SendClasslistToCoreView,
    SendPQVInitializeDB,
    CoreDBStatusView,
    CoreDBRefreshStatus,
    )

urlpatterns = [
    path('', ConnectServerManagerView.as_view(), name='connect_manager'),
    path('initial/', AttemptCoreConnectionView.as_view(), name='attempt_core_connection'),
    path('signup_manager/', AttemptCoreManagerLoginView.as_view(), name='attempt_manager_signup'),
    path('forget/initial/', ForgetCoreConnectionView.as_view(), name="forget_core_connection"),
    path('forget/manager/', ForgetCoreManagerLoginView.as_view(), name="forget_manager_connection"),
    path('send_info/', ConnectSendInfoToCoreView.as_view(), name='connect_send_info'),
    path('send_info/test_spec/', SendTestSpecToCoreView.as_view(), name='connect_send_spec'),
    path('send_info/classlist/', SendClasslistToCoreView.as_view(), name='connect_send_classlist'),
    path('send_info/init_db/', SendPQVInitializeDB.as_view(), name='connect_init_db'),
    path('send_info/init_db/<str:huey_id>', CoreDBStatusView.as_view(), name='connect_db_status'),
    path('send_info/init_db/<str:huey_id>/update/', CoreDBRefreshStatus.as_view(), name='connect_db_update')
]
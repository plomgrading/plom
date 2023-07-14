from django.urls import path
from UserManagement import views

urlpatterns = [
    path("users", view=views.UserPage.as_view(), name="users"),
    path("users/<str:username>", views.UserPage.as_view(), name="change_user_status"),
    # path("users/refresh/", views.UserPage.retryConnection, name="retry_user_page"),
    path("disableScanners/", views.UserPage.disableScanners, name="disableScanners"),
    path("enableScanners/", views.UserPage.enableScanners, name="enableScanners"),
    path("disableMarkers/", views.UserPage.disableMarkers, name="disableMarkers"),
    path("enableMarkers/", views.UserPage.enableMarkers, name="enableMarkers"),
    path("progress/<str:username>", view=views.ProgressPage.as_view(), name="progress"),
]

from django.urls import path
from UserManagement import views

urlpatterns = [
     path('users', view=views.UserPage.as_view(), name='listUsers'),
     path('users/<str:username>', views.changeStatus),
     path('disableScanners/', views.disableScanners, name='disableScanners'),
     path('enableScanners/', views.enableScanners, name='enableScanners'),
     path('disableMarkers/', views.disableMarkers, name='disableMarkers'),
     path('enableMarkers/', views.enableMarkers, name='enableMarkers'),
]

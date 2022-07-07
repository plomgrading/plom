from django.urls import path

import Authentication.views
from . import views

urlpatterns = [
    path('login/', Authentication.views.LoginView.as_view(), name="login"),  # newly added
    path('logout/', Authentication.views.LogoutView.as_view(), name="logout"),
    # testing home page
    path('', views.home, name='home'),

    # signup path
    path('signup/manager/', Authentication.views.SignupManager.as_view(), name="signup_manager"),
    path('activate/<slug:uidb64>/<slug:token>/', views.activate, name='activate'),
    # path('signup/'),
    # path('signup/marker/'),
    # path('signup/scanner/'),
]

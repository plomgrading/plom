from django.urls import path

import Authentication.views

# from . import views

urlpatterns = [
    path('login/', Authentication.views.LoginView.as_view(), name="login"),  # newly added
    path('logout/', Authentication.views.LogoutView.as_view(), name="logout"),

    path('', Authentication.views.Home.as_view(), name='home'),
    path('maintenance/', Authentication.views.Maintenance.as_view(), name='maintenance'),

    # signup path
    path('signup/manager/', Authentication.views.SignupManager.as_view(), name="signup_manager"),
    path('reset/<slug:uidb64>/<slug:token>/', Authentication.views.SetPassword.as_view(), name='password_reset'),
    path('reset/done/', Authentication.views.SetPasswordComplete.as_view(), name='password_reset_complete'),
    # path('signup/'),
    # path('signup/marker/'),
    # path('signup/scanner/'),
    path('passwordresetlinks/', Authentication.views.PasswordResetLinks.as_view(), name='password_reset'),
]

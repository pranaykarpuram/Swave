from django.urls import path
from .views import (
    test_itunes, 
    register, 
    login_view, 
    refresh_token, 
    profile, 
    update_profile, 
    logout,
    verify_firebase_token_view
)

urlpatterns = [
    path("test-itunes/", test_itunes),
    
    # Authentication endpoints
    path("auth/register/", register, name="register"),
    path("auth/login/", login_view, name="login"),
    path("auth/refresh/", refresh_token, name="refresh"),
    path("auth/logout/", logout, name="logout"),
    path("auth/verify-firebase/", verify_firebase_token_view, name="verify_firebase"),
    
    # User profile endpoints
    path("auth/profile/", profile, name="profile"),
    path("auth/profile/update/", update_profile, name="update_profile"),
]

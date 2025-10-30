from django.urls import path
from .views import (
    test_itunes,
    register,
    login_view,
    refresh_token,
    profile,
    update_profile,
    logout,
    verify_firebase_token_view,

    # music / swipe / playlist
    swipe,
    likes,
    build_daily_playlist,
    get_daily_playlist,

    # feed / recommendation style
    feed_next,
    swipe_event,
)

urlpatterns = [
    path("test-itunes/", test_itunes),

    # Authentication
    path("auth/register/", register, name="register"),
    path("auth/login/", login_view, name="login"),
    path("auth/refresh/", refresh_token, name="refresh"),
    path("auth/logout/", logout, name="logout"),
    path("auth/verify-firebase/", verify_firebase_token_view, name="verify_firebase"),
    
    # User profile
    path("auth/profile/", profile, name="profile"),
    path("auth/profile/update/", update_profile, name="update_profile"),

    # Music interactions on the app
    path("swipes/", swipe),
    path("likes/", likes),
    path("playlist/daily/build/", build_daily_playlist),
    path("playlist/daily/", get_daily_playlist),

    # Track feed for each user
    path("api/feed/next", feed_next),
    path("api/event/swipe", swipe_event),
]
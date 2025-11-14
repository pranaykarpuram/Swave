from django.urls import path
from .views import (
    test_itunes, 
    register, 
    login_view, 
    refresh_token, 
    profile, 
    update_profile, 
    logout,
    feed_next,
    swipe_event,
    spotify_login,
    spotify_callback,
    spotify_sync_likes, 
    spotify_test_playlist,
    spotify_test_playlist_browser,
)

urlpatterns = [
    path("test-itunes/", test_itunes),
    
    # Authentication endpoints
    path("auth/register/", register, name="register"),
    path("auth/login/", login_view, name="login"),
    path("auth/refresh/", refresh_token, name="refresh"),
    path("auth/logout/", logout, name="logout"),
    
    # User profile endpoints
    path("auth/profile/", profile, name="profile"),
    path("auth/profile/update/", update_profile, name="update_profile"),

    # Track flow
    path("api/feed/next", feed_next),
    path("api/event/swipe", swipe_event),

    #spotify
    path("auth/spotify/login", spotify_login, name="spotify_login"),
    path("auth/spotify/callback", spotify_callback, name="spotify_callback"),
    path("api/spotify/sync-likes", spotify_sync_likes, name="spotify_sync_likes"),
    path("spotify/test-playlist/", spotify_test_playlist),
    path("spotify/test-playlist-browser/", spotify_test_playlist_browser),

]

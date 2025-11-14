from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from .itunes import itunes_song_search
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer,
    UserWithProvidersSerializer
)
from .models import User, Track, SwipeEvent, ProviderToken, UserTrackLike

from . import reccomendations as ph
import random

import base64
import datetime
import json
import requests
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone
from django.shortcuts import redirect

from .spotify_playlist_export import create_spotify_playlist

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API = "https://api.spotify.com/v1"


def _demo_user(request):
    """
    TEMP: REMOVE once abhiram finishes firebase stuff
    """
    if request.user and request.user.is_authenticated:
        return request.user
    user, _ = User.objects.get_or_create(username="demo_spotify", defaults={"email": "demo@swave.local"})
    return user

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def spotify_test_playlist(request):
    user = request.user

    test_tracks = [
        "spotify:track:4uLU6hMCjMI75M1A2tKUQC",
        "spotify:track:3FAJ6O0NOHQV8Mc5Ri6ENp",
    ]

    from .spotify_playlist_export import create_spotify_playlist

    playlist = create_spotify_playlist(
        user=user,
        name="Swave Test Playlist",
        track_uris=test_tracks
    )

    return Response({
        "ok": True,
        "playlist_url": playlist["external_urls"]["spotify"],
        "playlist_id": playlist["id"]
    })

@api_view(["GET"])
@permission_classes([AllowAny])
def spotify_test_playlist_browser(request):
    from .views import _demo_user
    user = _demo_user(request)

    from .spotify_playlist_export import create_spotify_playlist

    test_tracks = [
        "spotify:track:4uLU6hMCjMI75M1A2tKUQC",
        "spotify:track:3FAJ6O0NOHQV8Mc5Ri6ENp",
    ]

    playlist = create_spotify_playlist(
        user=user,
        name="Swave Test Playlist (Browser)",
        track_uris=test_tracks,
    )

    return Response({
        "ok": True,
        "playlist_url": playlist["external_urls"]["spotify"],
        "playlist_id": playlist["id"]
    })

@api_view(["GET"])
@permission_classes([AllowAny])  # flip to IsAuthenticated after demo
def spotify_login(request):
    params = {
        "client_id": settings.SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "scope": settings.SPOTIFY_SCOPES,
        "show_dialog": "true",
    }
    return redirect(f"{SPOTIFY_AUTH_URL}?{urlencode(params)}")

@api_view(["GET"])
@permission_classes([AllowAny])  # flip to IsAuthenticated after demo
def spotify_callback(request):
    code = request.GET.get("code")
    if not code:
        return Response({"error": "missing_code"}, status=400)

    basic = base64.b64encode(
        f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": settings.SPOTIFY_REDIRECT_URI},
        headers={"Authorization": f"Basic {basic}"},
        timeout=15,
    )
    if resp.status_code != 200:
        return Response({"error": "token_exchange_failed", "detail": resp.text}, status=400)

    tok = resp.json()
    access = tok["access_token"]
    refresh = tok.get("refresh_token")
    expires_at = timezone.now() + datetime.timedelta(seconds=tok.get("expires_in", 3600))

    me = requests.get(f"{SPOTIFY_API}/me", headers={"Authorization": f"Bearer {access}"}, timeout=15)
    if me.status_code != 200:
        return Response({"error": "me_failed", "detail": me.text}, status=400)
    spotify_user_id = me.json()["id"]

    user = _demo_user(request)
    scopes = settings.SPOTIFY_SCOPES.split()

    ProviderToken.objects.update_or_create(
        user=user, provider="spotify",
        defaults={
            "access_token": access,
            "refresh_token": refresh,
            "token_type": tok.get("token_type", "Bearer"),
            "expires_at": expires_at,
            "provider_user_id": spotify_user_id,
            "scope": json.dumps(scopes),
        },
    )
    return Response({"ok": True, "connected": True, "spotify_user_id": spotify_user_id})

def _ensure_access_token(user):
    tok = ProviderToken.objects.filter(user=user, provider="spotify").first()
    if not tok:
        return None
    if tok.expires_at <= timezone.now() + datetime.timedelta(seconds=30) and tok.refresh_token:
        basic = base64.b64encode(
            f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()
        ).decode()
        r = requests.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": tok.refresh_token},
            headers={"Authorization": f"Basic {basic}"},
            timeout=15,
        )
        if r.status_code == 200:
            j = r.json()
            tok.access_token = j["access_token"]
            if "refresh_token" in j:
                tok.refresh_token = j["refresh_token"]
            tok.expires_at = timezone.now() + datetime.timedelta(seconds=j.get("expires_in", 3600))
            tok.token_type = j.get("token_type", tok.token_type)
            tok.save()
        else:
            return None
    return tok.access_token


def _upsert_saved_track(user, saved_item):
    track = saved_item["track"]
    tid = track["id"]
    title = track["name"]
    artists = ", ".join(a["name"] for a in track["artists"]) or ""
    album_art = (track.get("album", {}).get("images") or [{}])[0].get("url")
    preview = track.get("preview_url")

    # Upsert Track row
    Track.objects.update_or_create(
        provider="spotify", provider_track_id=tid,
        defaults={
            "title": title,
            "artist": artists,
            "album_art_url": album_art,
            "preview_url": preview,
        },
    )

    # Upsert UserTrackLike
    added_at = saved_item.get("added_at")
    dt = None
    if added_at:
        try:
            dt = datetime.datetime.fromisoformat(added_at.replace("Z", "+00:00"))
        except Exception:
            pass

    UserTrackLike.objects.update_or_create(
        user=user, provider="spotify", provider_track_id=tid,
        defaults={"added_at": dt},
    )

@api_view(["POST"])
@permission_classes([AllowAny])  # flip to IsAuthenticated after demo
def spotify_sync_likes(request):
    user = _demo_user(request)
    access = _ensure_access_token(user)
    if not access:
        return Response({"error": "not_connected"}, status=400)

    headers = {"Authorization": f"Bearer {access}"}
    url = f"{SPOTIFY_API}/me/tracks?limit=50"
    total = 0

    while url:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return Response({"error": "spotify_failed", "detail": r.text}, status=400)
        j = r.json()
        for item in j.get("items", []):
            _upsert_saved_track(user, item)
            total += 1
        url = j.get("next")  # Spotify gives a full URL for pagination

    return Response({"ok": True, "imported": total})

def _attach_preview(t):
    if t.get("preview_url"):
        return t
    res = itunes_song_search(f"{t['title']} {t['artist']}")
    if res:
        t["preview_url"] = res[0]["preview"]
        t["album_art_url"] = res[0]["artwork"]
    else:
        t["preview_url"] = ""
        t["album_art_url"] = ""
    return t

def _normalize_min(t: dict) -> dict:
    return {
        "id": t["id"],
        "title": t["title"],
        "artist": t["artist"],
        "album_art_url": t.get("album_art_url", ""),
        "preview_url": t.get("preview_url", "")
    }

@api_view(["GET"])
@permission_classes([AllowAny])
def feed_next(request):
    """
    If you pass ?liked=t1,t7,t12 it uses recommend_for_user().
    otherwise it just returns a random batch from tracks.
    """
    k = int(request.query_params.get("k", 20))
    liked = request.query_params.get("liked")

    clips = []
    if liked:
        liked_ids = [s for s in liked.split(",") if s]
        try:
            recs, _ = ph.recommend_for_user(liked_ids, k=min(k, len(ph.TRACKS)))
            rec_tracks = [_attach_preview(t) for _, t in recs]
            clips = [_normalize_min(t) for t in rec_tracks]
        except Exception:
            clips = []

    if not clips:
        pool = list(ph.TRACKS)
        random.shuffle(pool)
        pool = [_attach_preview(t) for t in pool[:k]]  
        clips = [_normalize_min(t) for t in pool]

    return Response({"batch_id": None, "next_cursor": None, "clips": clips})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def swipe_event(request):
    data = request.data or {}
    track_id = data.get("track_id")
    direction = data.get("direction")
    if direction not in ("left", "right") or not track_id:
        return Response({"error":"track_id and direction required"}, status=status.HTTP_400_BAD_REQUEST)

    from . import reccomendations as ph
    track = next((t for t in ph.TRACKS if t["id"] == track_id), None)

    SwipeEvent.objects.create(
        user=request.user,
        track_ext_id=track_id,
        direction=direction,
        batch_id=data.get("batch_id"),
        title=(track or {}).get("title"),
        artist=(track or {}).get("artist"),
    )
    return Response({"ok": True}, status=status.HTTP_201_CREATED)

@api_view(["GET"])
@permission_classes([AllowAny])
def test_itunes(request):
    q = request.GET.get("q")
    if not q:
        return Response({"error": "Missing 'q' query parameter"}, status=400)
    results = itunes_song_search(q)
    return Response(results)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
    print(f"Registration request data: {request.data}")
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)
    print(f"Registration validation errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login user and return JWT tokens"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """Refresh JWT access token"""
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        refresh = RefreshToken(refresh_token)
        return Response({
            'access': str(refresh.access_token),
        })
    except Exception as e:
        return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get current user profile"""
    serializer = UserWithProvidersSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile"""
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout user (blacklist refresh token)"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


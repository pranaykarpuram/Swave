import random
from django.utils.timezone import now

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import login

from .itunes import itunes_song_search
from .models import (
    User,
    Track,
    SwipeEvent,
    Playlist,
    PlaylistItem,
)
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserWithProvidersSerializer,
    TrackSerializer,
    SwipeSerializer,
    PlaylistSerializer,
)

from . import reccomendations as ph  # recommendation logic / TRACKS etc.


# Try to import Firebase, fallback gracefully if not configured
try:
    from .firebase_config import verify_firebase_token
    FIREBASE_ENABLED = True
except ImportError:
    FIREBASE_ENABLED = False
    print("Firebase Admin not configured")


def _attach_preview(t):
    """
    Ensure each recommended track dict has preview_url and artwork.
    Falls back to iTunes lookup if needed.
    """
    if t.get("preview_url") or t.get("preview"):
        # normalize keys
        if "preview" in t and "preview_url" not in t:
            t["preview_url"] = t["preview"]
        return t

    res = itunes_song_search(f"{t['title']} {t['artist']}")
    if res:
        # our itunes helper returns keys preview_url/artwork
        t["preview_url"] = res[0].get("preview_url", "")
        t["album_art_url"] = res[0].get("artwork", "")
    else:
        t["preview_url"] = ""
        t["album_art_url"] = ""
    return t


def _normalize_min(t: dict) -> dict:
    """Minified track info for frontend consumption."""
    return {
        "id": t.get("id") or t.get("external_id") or "",
        "title": t.get("title", ""),
        "artist": t.get("artist", ""),
        "album_art_url": t.get("album_art_url", t.get("artwork", "")),
        "preview_url": t.get("preview_url", ""),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def feed_next(request):
    """
    GET /api/feed/next?k=20&liked=id1,id2,...
    If ?liked=... is provided, recommend based on those liked IDs.
    Otherwise return a shuffled batch from ph.TRACKS.
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
    """Record a left/right swipe using relational Track rows."""
    data = request.data or {}
    track_id = data.get("track_id")
    direction = data.get("direction")
    if direction not in ("left", "right") or not track_id:
        return Response({"error": "track_id and direction required"}, status=status.HTTP_400_BAD_REQUEST)

    action = "like" if direction == "right" else "dislike"

    # find track in the database by external_id OR provider ID
    track_obj = (
        Track.objects.filter(external_id=track_id).first()
        or Track.objects.filter(provider_track_id=track_id).first()
    )

    if track_obj:
        SwipeEvent.objects.create(
            user=request.user,
            track=track_obj,
            action=action,
            played_ms=int(data.get("played_ms") or 0),
        )

    return Response({"ok": True}, status=status.HTTP_201_CREATED)


# itunes test endpoint
@api_view(["GET"])
@permission_classes([AllowAny])
def test_itunes(request):
    q = request.GET.get("q")
    if not q:
        return Response({"error": "Missing 'q' query parameter"}, status=400)
    results = itunes_song_search(q)
    return Response(results)


# auth / profile / session
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
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
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
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
    refresh_token_val = request.data.get('refresh')
    if not refresh_token_val:
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(refresh_token_val)
        return Response({'access': str(refresh.access_token)})
    except Exception:
        return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    serializer = UserWithProvidersSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token_val = request.data.get('refresh')
        if refresh_token_val:
            token = RefreshToken(refresh_token_val)
            token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_firebase_token_view(request):
    """Verify Firebase ID token and return Django JWT tokens"""
    firebase_token = request.data.get('firebase_token')
    if not firebase_token:
        return Response({'error': 'Firebase token required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not FIREBASE_ENABLED:
        return Response({'error': 'Firebase verification not configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    decoded_token = verify_firebase_token(firebase_token)
    if not decoded_token:
        return Response({'error': 'Invalid Firebase token'}, status=status.HTTP_401_UNAUTHORIZED)
    
    email = decoded_token.get('email')
    if not email:
        return Response({'error': 'No email in Firebase token'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        username = email.split('@')[0]
        user = User.objects.create_user(
            username=username,
            email=email,
            display_name=username
        )
        from .models import UserProfile
        UserProfile.objects.create(user=user)
    
    refresh = RefreshToken.for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    })


# music interactions using the relational DB
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def swipe(request):
    """
    Record a like/dislike for the logged-in user using normalized Track rows.
    Body should contain a 'track' object with external_id/title/artist/etc.
    """
    data = request.data
    track_data = data.get("track")
    if not track_data:
        return Response({"error": "Missing track"}, status=400)

    track, _ = Track.objects.get_or_create(
        external_id=track_data["external_id"],
        defaults={
            "title": track_data["title"],
            "artist": track_data["artist"],
            "preview_url": track_data.get("preview_url"),
            "artwork": track_data.get("artwork", ""),
            "source": track_data.get("source", "itunes"),
            "duration_ms": track_data.get("duration_ms"),
            "album_art_url": track_data.get("artwork", ""),
            "provider_track_id": track_data.get("external_id", ""),
        }
    )

    for f in ["title", "artist", "preview_url", "artwork", "source", "duration_ms", "album_art_url", "provider_track_id"]:
        val = track_data.get(f) or (f == "album_art_url" and track_data.get("artwork"))
        if val and getattr(track, f, None) != val:
            setattr(track, f, val)
    track.save()

    ev = SwipeEvent.objects.create(
        user=request.user,
        track=track,
        action=data.get("action", "like"),
        played_ms=int(data.get("played_ms") or 0),
    )
    return Response(SwipeSerializer(ev).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def likes(request):
    qs = (
        SwipeEvent.objects
        .filter(user=request.user, action="like")
        .select_related("track")
        .order_by("-created_at")
    )
    return Response(SwipeSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def build_daily_playlist(request):
    """Create/refresh today's playlist from today's likes."""
    today = now().date()
    pl, _ = Playlist.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={"name": f"Daily {today.isoformat()}"}
    )

    pl.items.all().delete()

    todays_likes = (
        SwipeEvent.objects
        .filter(user=request.user, action="like", created_at__date=today)
        .select_related("track")
        .order_by("created_at")
    )

    for i, ev in enumerate(todays_likes):
        PlaylistItem.objects.create(
            playlist=pl,
            track=ev.track,
            position=i
        )

    return Response(PlaylistSerializer(pl).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_daily_playlist(request):
    today = now().date()
    try:
        pl = Playlist.objects.get(user=request.user, date=today)
    except Playlist.DoesNotExist:
        return Response({"error": "no daily playlist yet"}, status=404)
    return Response(PlaylistSerializer(pl).data)
import random
from django.utils.timezone import now

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import login

from .itunes import itunes_song_search
from .models import (
    User,
    Track,
    SwipeEvent,
    Playlist,
    PlaylistItem,
)
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserWithProvidersSerializer,
    TrackSerializer,
    SwipeSerializer,
    PlaylistSerializer,
)

from . import reccomendations as ph  # recommendation logic / TRACKS etc.


#
# helper functions from main branch
#

# Try to import Firebase, fallback gracefully if not configured
try:
    from .firebase_config import verify_firebase_token
    FIREBASE_ENABLED = True
except ImportError:
    FIREBASE_ENABLED = False
    print("Firebase Admin not configured")

def _attach_preview(t):
    """
    Ensure each recommended track dict has preview_url and artwork.
    Falls back to iTunes lookup if needed.
    """
    if t.get("preview_url") or t.get("preview"):
        # normalize keys
        if "preview" in t and "preview_url" not in t:
            t["preview_url"] = t["preview"]
        return t

    res = itunes_song_search(f"{t['title']} {t['artist']}")
    if res:
        # res[0] is from itunes_song_search (your version returns "preview_url" and "artwork")
        t["preview_url"] = res[0].get("preview_url", "")
        t["album_art_url"] = res[0].get("artwork", "")
    else:
        t["preview_url"] = ""
        t["album_art_url"] = ""
    return t


def _normalize_min(t: dict) -> dict:
    """
    Minified track info to send to frontend.
    """
    return {
        "id": t.get("id") or t.get("external_id") or "",
        "title": t.get("title", ""),
        "artist": t.get("artist", ""),
        "album_art_url": t.get("album_art_url", t.get("artwork", "")),
        "preview_url": t.get("preview_url", ""),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def feed_next(request):
    """
    GET /api/feed/next?k=20&liked=id1,id2,...
    If ?liked=... is provided, recommend based on those liked IDs.
    Otherwise return a shuffled batch from ph.TRACKS.
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
    """
    Record a swipe event (left/right) for analytics / training.
    This version is from main, but we'll adapt it to our relational model
    where possible.
    """
    data = request.data or {}
    track_id = data.get("track_id")
    direction = data.get("direction")
    if direction not in ("left", "right") or not track_id:
        return Response({"error": "track_id and direction required"}, status=status.HTTP_400_BAD_REQUEST)

    # map the likes/dislikes
    action = "like" if direction == "right" else "dislike"

<<<<<<< HEAD
    SwipeEvent.objects.create(
        user=request.user,
        track_ext_id=track_id,
        direction=direction,
        batch_id=data.get("batch_id"),
        title=(track or {}).get("title"),
        artist=(track or {}).get("artist"),
=======
    # find track in the database by external_id OR provider ID
    track_obj = (
        Track.objects.filter(external_id=track_id).first()
        or Track.objects.filter(provider_track_id=track_id).first()
>>>>>>> origin/main
    )

    # logging an event with the track foreign key id
    if track_obj:
        SwipeEvent.objects.create(
            user=request.user,
            track=track_obj,
            action=action,
            played_ms=int(data.get("played_ms") or 0),
        )
    else:
        # If we truly can't resolve this into Track, just create nothing
        # (or you could choose to create a placeholder Track here)
        pass

    return Response({"ok": True}, status=status.HTTP_201_CREATED)


#
# itunes test endpoint
#

@api_view(["GET"])
@permission_classes([AllowAny])
def test_itunes(request):
    q = request.GET.get("q")
    if not q:
        return Response({"error": "Missing 'q' query parameter"}, status=400)
    results = itunes_song_search(q)
    return Response(results)


#
# auth / profile / session
#

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
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
    refresh_token_val = request.data.get('refresh')
    if not refresh_token_val:
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(refresh_token_val)
        return Response({
            'access': str(refresh.access_token),
        })
    except Exception:
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
        refresh_token_val = request.data.get('refresh')
        if refresh_token_val:
            token = RefreshToken(refresh_token_val)
            token.blacklist()
        return Response({'message': 'Successfully logged out'})
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


<<<<<<< HEAD
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_firebase_token_view(request):
    """Verify Firebase ID token and return Django JWT tokens"""
    firebase_token = request.data.get('firebase_token')
    if not firebase_token:
        return Response({'error': 'Firebase token required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not FIREBASE_ENABLED:
        return Response({'error': 'Firebase verification not configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    decoded_token = verify_firebase_token(firebase_token)
    if not decoded_token:
        return Response({'error': 'Invalid Firebase token'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Get user email from Firebase token
    firebase_uid = decoded_token.get('uid')
    email = decoded_token.get('email')
    
    if not email:
        return Response({'error': 'No email in Firebase token'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get or create Django user
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Create user if doesn't exist
        username = email.split('@')[0]  # Use email prefix as username
        user = User.objects.create_user(
            username=username,
            email=email,
            display_name=email.split('@')[0]
        )
        from .models import UserProfile
        UserProfile.objects.create(user=user)
    
    # Return Django JWT tokens
    refresh = RefreshToken.for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    })

=======
#
# music interactions using the relational DB
#

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def swipe(request):
    """
    Record a like/dislike for the logged-in user using normalized Track rows.
    Body should contain:
    {
        "action": "like" | "dislike",
        "played_ms": <int>,
        "track": {
            "external_id": "...",
            "title": "...",
            "artist": "...",
            "preview_url": "...",
            "artwork": "...",
            "source": "itunes",
            "duration_ms": 12345
        }
    }
    """
    data = request.data
    track_data = data.get("track")
    if not track_data:
        return Response({"error": "Missing track"}, status=400)

    track, _ = Track.objects.get_or_create(
        external_id=track_data["external_id"],
        defaults={
            "title": track_data["title"],
            "artist": track_data["artist"],
            "preview_url": track_data["preview_url"],
            "artwork": track_data.get("artwork", ""),
            "source": track_data.get("source", "itunes"),
            "duration_ms": track_data.get("duration_ms"),
            "album_art_url": track_data.get("artwork", ""),
            "provider_track_id": track_data.get("external_id", ""),
        }
    )

    # refresh data if changed
    for f in ["title", "artist", "preview_url", "artwork", "source", "duration_ms", "album_art_url", "provider_track_id"]:
        val = track_data.get(f) or (f == "album_art_url" and track_data.get("artwork"))
        if val and getattr(track, f, None) != val:
            setattr(track, f, val)
    track.save()

    ev = SwipeEvent.objects.create(
        user=request.user,
        track=track,
        action=data.get("action", "like"),
        played_ms=int(data.get("played_ms") or 0),
    )
    return Response(SwipeSerializer(ev).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def likes(request):
    qs = (
        SwipeEvent.objects
        .filter(user=request.user, action="like")
        .select_related("track")
        .order_by("-created_at")
    )
    return Response(SwipeSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def build_daily_playlist(request):
    """Create/refresh today's playlist from today's likes."""
    today = now().date()
    pl, _ = Playlist.objects.get_or_create(
        user=request.user,
        date=today,
        defaults={"name": f"Daily {today.isoformat()}"}
    )

    # reset 
    pl.items.all().delete()

    todays_likes = (
        SwipeEvent.objects
        .filter(user=request.user, action="like", created_at__date=today)
        .select_related("track")
        .order_by("created_at")
    )

    for i, ev in enumerate(todays_likes):
        PlaylistItem.objects.create(
            playlist=pl,
            track=ev.track,
            position=i
        )

    return Response(PlaylistSerializer(pl).data, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_daily_playlist(request):
    today = now().date()
    try:
        pl = Playlist.objects.get(user=request.user, date=today)
    except Playlist.DoesNotExist:
        return Response({"error": "no daily playlist yet"}, status=404)
    return Response(PlaylistSerializer(pl).data)
>>>>>>> origin/main

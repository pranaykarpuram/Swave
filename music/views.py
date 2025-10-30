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
from .models import User

from django.utils.timezone import now
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Track, SwipeEvent, Playlist, PlaylistItem
from .serializers import TrackSerializer, SwipeSerializer, PlaylistSerializer


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


# music stuff

@api_view(["POST"])
@permission_classes([AllowAny])
def swipe(request):
    """Record a like/dislike for the logged-in user."""
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
        }
    )
    # optional: light metadata refresh
    for f in ["title","artist","preview_url","artwork","source","duration_ms"]:
        val = track_data.get(f)
        if val and getattr(track, f) != val:
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
@permission_classes([AllowAny])
def likes(request):
    qs = (SwipeEvent.objects
          .filter(user=request.user, action="like")
          .select_related("track")
          .order_by("-created_at"))
    return Response(SwipeSerializer(qs, many=True).data)

@api_view(["POST"])
@permission_classes([AllowAny])
def build_daily_playlist(request):
    """Create/refresh today's playlist from today's likes."""
    today = now().date()
    pl, _ = Playlist.objects.get_or_create(
        user=request.user, date=today, defaults={"name": f"Daily {today.isoformat()}"}
    )
    pl.items.all().delete()
    todays_likes = (SwipeEvent.objects
                    .filter(user=request.user, action="like", created_at__date=today)
                    .select_related("track")
                    .order_by("created_at"))
    for i, ev in enumerate(todays_likes):
        PlaylistItem.objects.create(playlist=pl, track=ev.track, position=i)
    return Response(PlaylistSerializer(pl).data, status=201)

@api_view(["GET"])
@permission_classes([AllowAny])
def get_daily_playlist(request):
    today = now().date()
    try:
        pl = Playlist.objects.get(user=request.user, date=today)
    except Playlist.DoesNotExist:
        return Response({"error": "no daily playlist yet"}, status=404)
    return Response(PlaylistSerializer(pl).data)
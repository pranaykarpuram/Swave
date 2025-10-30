from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from .itunes import itunes_song_search
from .models import SwipeEvent, Track
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer,
    UserWithProvidersSerializer
)
from .models import User
from . import reccomendations as ph
import random

def _attach_preview(t):
    if t.get("preview_url"):
        return t
    res = itunes_song_search(f"{t['title']} {t['artist']}")
    if res:
        t["preview_url"] = res[0]["preview"]
    else:
        t["preview_url"] = ""
    return t

def _normalize_min(t: dict) -> dict:
    return {
        "id": t["id"],
        "title": t["title"],
        "artist": t["artist"],
    }

@api_view(["GET"])
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
        user_id=request.user.id,
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


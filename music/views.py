from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .itunes import itunes_song_search

@api_view(["GET"])
@permission_classes([AllowAny])
def test_itunes(request):
    q = request.GET.get("q", "taylor swift")
    results = itunes_song_search(q)
    return Response(results)


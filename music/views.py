from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .itunes import itunes_song_search

@api_view(["GET"])
@permission_classes([AllowAny])
def test_itunes(request):
    q = request.GET.get("q")
    if not q:
        return Response({"error": "Missing 'q' query parameter"}, status=400)
    results = itunes_song_search(q)
    return Response(results)


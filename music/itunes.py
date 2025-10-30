import requests

def itunes_song_search(query):
    url = "https://itunes.apple.com/search"
    params = {
        "term": query,
        "country": "US",
        "media": "music",
        "entity": "song",
        "limit": 10,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    results = []
    for song in data.get("results", []):
        if song.get("previewUrl"):
            results.append({
                "external_id": str(song.get("trackId")),
                "title": song.get("trackName"),
                "artist": song.get("artistName"),
                "preview_url": song.get("previewUrl"),
                "artwork": song.get("artworkUrl100"),
                "source": "itunes",
                "duration_ms": song.get("trackTimeMillis"),
            })
    return results

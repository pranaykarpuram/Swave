from math import sqrt

# ---- 1) Sample dataset (Spotify-like features) ----------------------------
# Each feature in [0,1] except tempo (BPM). We'll normalize tempo to [0,1].
# Fields: id, title, artist, features = [danceability, energy, speechiness, acousticness, instrumentalness, liveness, valence, tempo_bpm]
TRACKS = [
    {"id":"t1", "title":"Midnight Drive",     "artist":"Neon Echo",      "feat":[0.78,0.65,0.06,0.12,0.00,0.18,0.52,118]},
    {"id":"t2", "title":"Rose Petals",        "artist":"Luna Waves",     "feat":[0.45,0.38,0.04,0.72,0.05,0.12,0.30, 82]},
    {"id":"t3", "title":"City Lights",        "artist":"Metro Bloom",    "feat":[0.81,0.72,0.07,0.10,0.00,0.15,0.63,124]},
    {"id":"t4", "title":"Ocean Study",        "artist":"Blue Atlas",     "feat":[0.22,0.20,0.04,0.92,0.80,0.08,0.18, 72]},
    {"id":"t5", "title":"Strobe Heart",       "artist":"Pixel Parade",   "feat":[0.76,0.83,0.05,0.05,0.00,0.14,0.61,128]},
    {"id":"t6", "title":"Coffee & Rain",      "artist":"Late Night",     "feat":[0.36,0.28,0.05,0.80,0.10,0.10,0.22, 78]},
    {"id":"t7", "title":"Gold Sneakers",      "artist":"Kite Kid",       "feat":[0.88,0.74,0.12,0.08,0.00,0.22,0.66,122]},
    {"id":"t8", "title":"Glass Garden",       "artist":"Terrarium",      "feat":[0.41,0.35,0.05,0.70,0.20,0.09,0.28, 90]},
    {"id":"t9", "title":"Afterglow",          "artist":"Sunset Run",     "feat":[0.70,0.60,0.06,0.20,0.00,0.18,0.55,110]},
    {"id":"t10","title":"Polar Air",          "artist":"North Circuit",  "feat":[0.32,0.30,0.06,0.78,0.35,0.11,0.25, 85]},
    {"id":"t11","title":"Velvet Static",      "artist":"Aurora Null",    "feat":[0.60,0.67,0.05,0.18,0.00,0.16,0.48,115]},
    {"id":"t12","title":"Morning Mango",      "artist":"Daybreak Duo",   "feat":[0.72,0.58,0.07,0.30,0.00,0.20,0.70,105]},
    {"id":"t13","title":"Paper Planes",       "artist":"Lo-Fi Lobby",    "feat":[0.55,0.42,0.05,0.65,0.25,0.10,0.34, 88]},
    {"id":"t14","title":"Thunder Run",        "artist":"Volt Avenue",    "feat":[0.64,0.85,0.06,0.10,0.00,0.28,0.46,132]},
    {"id":"t15","title":"Indigo Letters",     "artist":"Distant Pines",  "feat":[0.27,0.24,0.04,0.88,0.55,0.07,0.20, 76]},
]

# ---- 2) Feature prep: normalize tempo to 0..1, keep others as-is ----------
def normalize_track_features(feat, tempo_min=60.0, tempo_max=200.0):
    *rest, tempo = feat
    tempo_norm = (tempo - tempo_min) / (tempo_max - tempo_min)
    # clamp
    tempo_norm = max(0.0, min(1.0, tempo_norm))
    return rest + [tempo_norm]

TRACKS_VEC = []
for t in TRACKS:
    vec = normalize_track_features(t["feat"])
    TRACKS_VEC.append({**t, "vec": vec})

# ---- 3) Similarity helpers -------------------------------------------------
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def norm(a): return sqrt(sum(x*x for x in a)) or 1.0
def cosine_sim(a, b): return dot(a, b) / (norm(a) * norm(b))

def average_vectors(vectors):
    n = len(vectors)
    if n == 0: return None
    dim = len(vectors[0])
    avg = [0.0]*dim
    for v in vectors:
        for i, x in enumerate(v):
            avg[i] += x
    return [x / n for x in avg]

# ---- 4) Core recommenders ---------------------------------------------------
def recommend_similar_to(track_id, k=5):
    base = next((t for t in TRACKS_VEC if t["id"] == track_id), None)
    if not base:
        raise ValueError(f"Unknown track id: {track_id}")
    scores = []
    for t in TRACKS_VEC:
        if t["id"] == track_id: 
            continue
        s = cosine_sim(base["vec"], t["vec"])
        scores.append((s, t))
    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:k], base

def recommend_for_user(liked_ids, k=7):
    liked = [t["vec"] for t in TRACKS_VEC if t["id"] in liked_ids]
    if not liked:
        raise ValueError("No liked tracks found for those IDs.")
    user_vec = average_vectors(liked)
    scores = []
    for t in TRACKS_VEC:
        if t["id"] in liked_ids: 
            continue
        s = cosine_sim(user_vec, t["vec"])
        scores.append((s, t))
    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:k], user_vec

# ---- 5) Pretty printing -----------------------------------------------------
def show_results(title, items):
    print("\n" + "="*len(title))
    print(title)
    print("="*len(title))
    for rank, (score, t) in enumerate(items, 1):
        print(f"{rank:2d}. {t['title']} — {t['artist']}   (sim={score:.3f}, id={t['id']})")

# ---- 6) Demo runs -----------------------------------------------------------
if __name__ == "__main__":
    # Demo A: "Find songs similar to a single track"
    top_sim, base = recommend_similar_to("t1", k=5)
    show_results(f'Similar to "{base["title"]}" by {base["artist"]}', top_sim)

    # Demo B: "User liked these tracks → give me recs"
    liked = ["t1", "t7", "t12"]  # tweak this set to change the vibe
    top_user, _ = recommend_for_user(liked, k=7)
    show_results(f"Recommendations based on likes {liked}", top_user)

    # Demo C: quick explanation line for the meeting
    print("\nNotes:")
    print("- We model each song as a feature vector (danceability, energy, speechiness, acousticness, instrumentalness, liveness, valence, tempo).")
    print("- We normalize tempo to match the 0–1 scale of other features.")
    print("- For a user, we average the vectors of liked tracks to get a 'vibe vector', then rank songs by cosine similarity.")

"""
Flask web frontend for the Letterboxd Movie Recommender.
"""

import os
import random
from collections import Counter
from flask import Flask, render_template, jsonify
from data_loader import load_export
from tmdb_client import get_film_data, get_popular_films
from recommender import get_recommendations

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROFILES = {
    "yukon47": {
        "display_name": "Karis",
        "export_dir": os.path.join(BASE_DIR, "..", "letterboxd-yukon47-2026-04-13-19-18-utc"),
        "avatar": "🎬",
    },
    "leeaalle": {
        "display_name": "Leealle",
        "export_dir": os.path.join(BASE_DIR, "..", "letterboxd-leeaalle-profile"),
        "avatar": "🍿",
    },
}

def get_profile_highlights(data: dict) -> dict:
    """Return top 5 rated films and top 4 favorites with OMDB posters."""
    highlights = {"top_rated": [], "favorites": []}

    # Top 5 rated
    if not data["ratings"].empty:
        top5 = data["ratings"].sort_values("Rating", ascending=False).head(5)
        for _, row in top5.iterrows():
            film = get_film_data(row["Name"], row["Year"])
            highlights["top_rated"].append({
                "title": row["Name"],
                "year": row["Year"],
                "rating": row["Rating"],
                "poster": film.get("poster", ""),
                "imdb_url": film.get("url", ""),
            })

    # Top 4 favorites
    for name, year in data["favorite_films"][:4]:
        if name and not name.startswith("https://"):
            film = get_film_data(name, year)
            highlights["favorites"].append({
                "title": name,
                "year": year,
                "poster": film.get("poster", ""),
                "imdb_url": film.get("url", ""),
            })

    return highlights


def build_recommendations(username: str) -> dict:
    profile = PROFILES[username]
    data = load_export(os.path.abspath(profile["export_dir"]))

    # Top rated + favorites for context
    ratings = data["ratings"]
    top_films = []
    if not ratings.empty:
        top = ratings.sort_values("Rating", ascending=False).head(8)
        top_films = [(row["Name"], row["Year"]) for _, row in top.iterrows()]

    seen = {name for name, _ in top_films}
    for name, year in data["favorite_films"]:
        if name and name not in seen and not name.startswith("https://"):
            top_films.append((name, year))
            seen.add(name)

    omdb_user_films = [get_film_data(name, year) for name, year in top_films]

    # Infer genres and build a large, shuffled candidate pool unique to this user
    user_genres = []
    for f in omdb_user_films:
        user_genres.extend(f.get("genres", []))
    top_genres = [g for g, _ in Counter(user_genres).most_common(6)]

    all_candidates = get_popular_films(user_genres=top_genres)
    unseen_candidates = [f for f in all_candidates if f["title"] not in data["watched_names"]]

    # Shuffle so each run picks different candidates → different recs each time
    random.shuffle(unseen_candidates)
    selected = unseen_candidates[:20]

    omdb_candidates = [get_film_data(f["title"], f["year"]) for f in selected]

    recs = get_recommendations(
        user_summary=data["summary"],
        scraped_top_films=omdb_candidates,
        scraped_user_films=omdb_user_films,
        favorite_films=data["favorite_films"],
        n=10,
    )

    # Enrich recs with poster + metadata
    for rec in recs:
        film = get_film_data(rec["title"], rec.get("year", ""))
        rec["poster"] = film.get("poster", "")
        rec["genres"] = film.get("genres", [])
        rec["description"] = film.get("description", "")
        rec["imdb_url"] = film.get("url", "")

    # Profile highlights (top rated + favorites)
    highlights = get_profile_highlights(data)

    return {"recs": recs, "highlights": highlights, "username": username}


@app.route("/")
def index():
    profiles = [
        {"username": k, "display_name": v["display_name"], "avatar": v["avatar"]}
        for k, v in PROFILES.items()
    ]
    return render_template("index.html", profiles=profiles)


@app.route("/recommendations/<username>")
def recommendations(username):
    if username not in PROFILES:
        return "Profile not found", 404
    return render_template("results.html", username=username, profile=PROFILES[username])


@app.route("/api/recommendations/<username>")
def api_recommendations(username):
    if username not in PROFILES:
        return jsonify({"error": "Profile not found"}), 404
    try:
        result = build_recommendations(username)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

"""
Loads and merges the local Letterboxd CSV export into a unified user profile.
"""

import os
import pandas as pd


def load_export(export_dir: str) -> dict:
    """
    Reads all relevant CSVs from the Letterboxd export folder and returns
    a dict of DataFrames plus a pre-built summary string for the AI prompt.
    """
    def read(filename):
        path = os.path.join(export_dir, filename)
        if os.path.exists(path):
            df = pd.read_csv(path)
            df.columns = df.columns.str.strip()
            return df
        return pd.DataFrame()

    ratings  = read("ratings.csv")
    reviews  = read("reviews.csv")
    diary    = read("diary.csv")
    watched  = read("watched.csv")
    liked    = read(os.path.join("likes", "films.csv"))
    profile  = read("profile.csv")

    username = ""
    favorite_film_names = []

    if not profile.empty and "Username" in profile.columns:
        username = profile["Username"].iloc[0]

    # Map known favorite film URLs to titles
    FAVORITE_URI_MAP = {
        "https://boxd.it/261M": ("Hairspray", 2007),
        "https://boxd.it/6JKY":  ("The Book of Life", 2014),
        "https://boxd.it/3VH2":  ("Guardians of the Galaxy", 2014),
        "https://boxd.it/9CL2":  ("Strange Magic", 2015),  # confirmed by user
    }

    if not profile.empty and "Favorite Films" in profile.columns:
        fav_raw = str(profile["Favorite Films"].iloc[0])
        fav_uris = [u.strip() for u in fav_raw.split(",") if u.strip()]
        for uri in fav_uris:
            if uri in FAVORITE_URI_MAP:
                favorite_film_names.append(FAVORITE_URI_MAP[uri][0])
            else:
                # fall back to cross-referencing ratings CSV
                if not ratings.empty:
                    match = ratings[ratings["Letterboxd URI"] == uri]
                    if not match.empty:
                        favorite_film_names.append(match.iloc[0]["Name"])

    # Build a clean merged view: all watched films with rating where available
    watched_names = set(watched["Name"].tolist()) if not watched.empty else set()

    # Liked film names
    liked_names = set(liked["Name"].tolist()) if not liked.empty else set()

    # Ratings dict  name -> rating
    ratings_map = {}
    if not ratings.empty:
        for _, row in ratings.iterrows():
            ratings_map[row["Name"]] = row["Rating"]

    # Reviews dict  name -> review text
    reviews_map = {}
    if not reviews.empty:
        for _, row in reviews.iterrows():
            if pd.notna(row.get("Review", None)) and str(row["Review"]).strip():
                reviews_map[row["Name"]] = str(row["Review"]).strip()

    # Build summary lines
    lines = []
    lines.append(f"User: {username}")
    lines.append(f"Total films watched: {len(watched_names)}")
    lines.append("")
    lines.append("=== LETTERBOXD FAVORITE FILMS (pinned on profile — highest priority) ===")
    for name in favorite_film_names:
        lines.append(f"  ★ {name}")
    lines.append("")
    lines.append("=== RATINGS ===")
    for _, row in ratings.sort_values("Rating", ascending=False).iterrows():
        liked_tag = " [liked]" if row["Name"] in liked_names else ""
        review_tag = f'  Review: "{reviews_map[row["Name"]]}"' if row["Name"] in reviews_map else ""
        lines.append(f"  {row['Name']} ({row['Year']}) — {row['Rating']}/5{liked_tag}{review_tag}")

    lines.append("")
    lines.append("=== WATCHED BUT NOT RATED ===")
    unrated = watched_names - set(ratings_map.keys())
    for name in sorted(unrated):
        lines.append(f"  {name}")

    lines.append("")
    lines.append("=== LIKED FILMS (heart) ===")
    for name in sorted(liked_names):
        lines.append(f"  {name}")

    summary = "\n".join(lines)

    return {
        "username": username,
        "ratings": ratings,
        "reviews": reviews,
        "diary": diary,
        "watched": watched,
        "liked": liked,
        "ratings_map": ratings_map,
        "liked_names": liked_names,
        "watched_names": watched_names,
        "favorite_films": favorite_film_names,
        "summary": summary,
    }

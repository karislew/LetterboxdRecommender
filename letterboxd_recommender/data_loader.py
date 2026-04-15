"""
Loads and merges the local Letterboxd CSV export into a unified user profile.
Fully dynamic — works for any user's export folder.
"""

import os
import pandas as pd


def load_export(export_dir: str) -> dict:
    def read(filename):
        path = os.path.join(export_dir, filename)
        if os.path.exists(path):
            df = pd.read_csv(path)
            df.columns = df.columns.str.strip()
            return df
        return pd.DataFrame()

    ratings = read("ratings.csv")
    reviews = read("reviews.csv")
    diary   = read("diary.csv")
    watched = read("watched.csv")
    liked   = read(os.path.join("likes", "films.csv"))
    profile = read("profile.csv")

    username = ""
    pronoun = ""
    favorite_films = []  # list of (name, year) tuples

    if not profile.empty:
        if "Username" in profile.columns:
            username = str(profile["Username"].iloc[0])
        if "Pronoun" in profile.columns:
            pronoun = str(profile["Pronoun"].iloc[0])

        # Resolve favorite film URIs dynamically by cross-referencing ratings + watched
        if "Favorite Films" in profile.columns:
            fav_raw = str(profile["Favorite Films"].iloc[0])
            fav_uris = [u.strip() for u in fav_raw.split(",") if u.strip()]

            # Build a URI -> (name, year) lookup from ratings and watched
            uri_map = {}
            for df in [ratings, watched]:
                if not df.empty and "Letterboxd URI" in df.columns:
                    for _, row in df.iterrows():
                        uri = str(row.get("Letterboxd URI", "")).strip()
                        name = str(row.get("Name", "")).strip()
                        year = row.get("Year", "")
                        if uri and name:
                            uri_map[uri] = (name, year)

            for uri in fav_uris:
                if uri in uri_map:
                    favorite_films.append(uri_map[uri])
                else:
                    # Store URI as placeholder if we can't resolve it
                    favorite_films.append((uri, ""))

    # Build lookup maps
    watched_names = set(watched["Name"].tolist()) if not watched.empty else set()
    liked_names = set(liked["Name"].tolist()) if not liked.empty else set()

    ratings_map = {}
    if not ratings.empty:
        for _, row in ratings.iterrows():
            ratings_map[row["Name"]] = row["Rating"]

    reviews_map = {}
    if not reviews.empty:
        for _, row in reviews.iterrows():
            if pd.notna(row.get("Review")) and str(row["Review"]).strip():
                reviews_map[row["Name"]] = str(row["Review"]).strip()

    # Build summary — trimmed to stay within token limits
    lines = []
    lines.append(f"User: {username}")
    if pronoun and pronoun != "nan":
        lines.append(f"Pronouns: {pronoun}")
    lines.append(f"Total films watched: {len(watched_names)}")

    lines.append("")
    lines.append("=== PINNED FAVORITE FILMS (highest priority taste signal) ===")
    if favorite_films:
        for name, year in favorite_films:
            year_str = f" ({year})" if year else ""
            lines.append(f"  ★ {name}{year_str}")
    else:
        lines.append("  (none listed)")

    lines.append("")
    lines.append("=== TOP RATED FILMS (4 stars and above) ===")
    if not ratings.empty:
        high = ratings[ratings["Rating"] >= 4].sort_values("Rating", ascending=False)
        for _, row in high.iterrows():
            liked_tag = " [liked]" if row["Name"] in liked_names else ""
            # Full review text restored
            review = reviews_map.get(row["Name"], "")
            review_tag = f'  Review: "{review}"' if review else ""
            lines.append(f"  {row['Name']} ({row['Year']}) — {row['Rating']}/5{liked_tag}{review_tag}")

    lines.append("")
    lines.append("=== LOW RATED FILMS (2 stars and below — avoid recommending similar) ===")
    if not ratings.empty:
        low = ratings[ratings["Rating"] <= 2].sort_values("Rating")
        for _, row in low.iterrows():
            lines.append(f"  {row['Name']} ({row['Year']}) — {row['Rating']}/5")

    lines.append("")
    lines.append("=== LIKED FILMS ===")
    for name in sorted(liked_names):
        lines.append(f"  {name}")

    summary = "\n".join(lines)

    return {
        "username": username,
        "pronoun": pronoun,
        "favorite_films": favorite_films,
        "ratings": ratings,
        "reviews": reviews,
        "diary": diary,
        "watched": watched,
        "liked": liked,
        "ratings_map": ratings_map,
        "liked_names": liked_names,
        "watched_names": watched_names,
        "summary": summary,
    }

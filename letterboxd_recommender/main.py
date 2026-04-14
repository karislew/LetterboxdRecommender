"""
Letterboxd Movie Recommender
-----------------------------
1. Loads any user's Letterboxd export CSV files
2. Fetches film metadata + ratings from OMDB (free official API)
3. Sends everything to Groq (LLaMA 3.3) for personalized recommendations

Usage:
    python main.py --export "/path/to/letterboxd-export-folder" --recs 10
"""

import argparse
import os
import sys

from data_loader import load_export
from tmdb_client import get_film_data, get_popular_films
from recommender import get_recommendations


def pick_top_user_films(data: dict, n: int = 8) -> list[tuple]:
    """Return the user's top-rated films as (name, year) tuples."""
    ratings = data["ratings"]
    if ratings.empty:
        return []
    top = ratings.sort_values("Rating", ascending=False).head(n)
    return [(row["Name"], row["Year"]) for _, row in top.iterrows()]


def main():
    parser = argparse.ArgumentParser(description="Letterboxd AI Recommender")
    parser.add_argument(
        "--export",
        default=os.path.join(
            os.path.dirname(__file__),
            "..",
            "letterboxd-yukon47-2026-04-13-19-18-utc",
        ),
        help="Path to your Letterboxd export folder",
    )
    parser.add_argument("--recs", type=int, default=10, help="Number of recommendations")
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip OMDB fetching (use only local CSV data)",
    )
    args = parser.parse_args()

    export_dir = os.path.abspath(args.export)
    if not os.path.isdir(export_dir):
        print(f"Error: export folder not found at {export_dir}")
        sys.exit(1)

    # ── Step 1: Load local data ──────────────────────────────────────────────
    print("📂 Loading Letterboxd export data...")
    data = load_export(export_dir)
    fav_names = [name for name, _ in data["favorite_films"] if name]
    print(
        f"   User: {data['username']} | "
        f"{len(data['watched_names'])} watched | "
        f"{len(data['ratings'])} ratings | "
        f"{len(data['liked_names'])} liked | "
        f"Favorites: {', '.join(fav_names) if fav_names else 'none'}"
    )

    omdb_user_films = []
    omdb_candidate_films = []

    if not args.no_fetch:
        # ── Step 2: Fetch metadata for top-rated + pinned favorites ──────────
        top_films = pick_top_user_films(data, n=8)

        # Merge in favorites without duplicating
        seen = {name for name, _ in top_films}
        for name, year in data["favorite_films"]:
            if name and name not in seen and not name.startswith("https://"):
                top_films.append((name, year))
                seen.add(name)

        print(f"\n🎬 Fetching OMDB metadata for {len(top_films)} films (top rated + favorites)...")
        for name, year in top_films:
            print(f"   → {name} ({year})")
            omdb_user_films.append(get_film_data(name, year))

        # ── Step 3: Fetch candidate films tailored to this user's genres ────
        print("\n🌐 Fetching candidate films via OMDB...")
        # Infer genre preferences from OMDB data of user's top films
        user_genres = []
        for f in omdb_user_films:
            user_genres.extend(f.get("genres", []))
        # Deduplicate, keep most common
        from collections import Counter
        top_genres = [g for g, _ in Counter(user_genres).most_common(6)]
        print(f"   Inferred genres from your history: {', '.join(top_genres) if top_genres else 'mixed'}")

        candidates = get_popular_films(user_genres=top_genres)
        unseen = [f for f in candidates if f["title"] not in data["watched_names"]][:15]
        print(f"   {len(unseen)} unseen candidates — fetching details...")
        for f in unseen:
            print(f"   → {f['title']} ({f['year']})")
            omdb_candidate_films.append(get_film_data(f["title"], f["year"]))
    else:
        print("\n⚡ Skipping OMDB fetch (--no-fetch flag set).")

    # ── Step 4: Generate AI recommendations ─────────────────────────────────
    print(f"\n🤖 Asking Groq for {args.recs} personalized recommendations for {data['username']}...")
    recommendations = get_recommendations(
        user_summary=data["summary"],
        scraped_top_films=omdb_candidate_films,
        scraped_user_films=omdb_user_films,
        favorite_films=data["favorite_films"],
        n=args.recs,
    )

    # ── Step 5: Print results ────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print(f"  🎬  MOVIE RECOMMENDATIONS FOR {data['username'].upper()}")
    print("═" * 60 + "\n")
    for line in recommendations.splitlines():
        print(line)
        if line.strip() and line.strip()[0].isdigit() and line.strip()[1] in ".)":
            print()
    print("\n" + "═" * 60)

    # Save to file
    out_path = os.path.join(os.path.dirname(__file__), f"recommendations_{data['username']}.txt")
    with open(out_path, "w") as f:
        f.write(f"Recommendations for {data['username']}\n")
        f.write("=" * 60 + "\n\n")
        f.write(recommendations)
    print(f"\n💾 Saved to {out_path}")


if __name__ == "__main__":
    main()

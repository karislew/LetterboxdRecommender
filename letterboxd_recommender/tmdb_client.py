"""
OMDB API client — fetches film metadata, ratings, and plot via the free OMDB API.
Free tier: 1,000 requests/day, no billing required.
Get a free key at: https://www.omdbapi.com/apikey.aspx
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "https://www.omdbapi.com"
DELAY = 0.25


def _key() -> str:
    key = os.getenv("OMDB_API_KEY")
    if not key:
        raise ValueError("OMDB_API_KEY not set in .env")
    return key


def get_film_data(name: str, year: int | str) -> dict:
    """
    Fetch film metadata from OMDB by title + year.
    Returns a unified dict the recommender expects.
    """
    result = {
        "title": name,
        "year": year,
        "genres": [],
        "avg_rating": None,
        "description": "",
        "top_reviews": [],
        "url": "",
    }

    params = {
        "apikey": _key(),
        "t": name,
        "y": str(year),
        "type": "movie",
        "plot": "short",
    }
    resp = requests.get(BASE, params=params, timeout=10)
    time.sleep(DELAY)

    if resp.status_code != 200:
        return result

    data = resp.json()
    if data.get("Response") == "False":
        # Try without year in case of slight mismatch
        params.pop("y")
        resp = requests.get(BASE, params=params, timeout=10)
        time.sleep(DELAY)
        data = resp.json()
        if data.get("Response") == "False":
            return result

    result["description"] = data.get("Plot", "")
    result["genres"] = [g.strip() for g in data.get("Genre", "").split(",") if g.strip()]
    result["url"] = f"https://www.imdb.com/title/{data.get('imdbID', '')}/"

    # Convert IMDb rating (0-10) to 0-5 scale
    imdb_rating = data.get("imdbRating", "N/A")
    if imdb_rating != "N/A":
        try:
            result["avg_rating"] = round(float(imdb_rating) / 2, 1)
        except ValueError:
            pass

    # OMDB doesn't have user reviews, but we can include Rotten Tomatoes score as context
    for rating in data.get("Ratings", []):
        if rating["Source"] == "Rotten Tomatoes":
            result["top_reviews"].append({
                "author": "Rotten Tomatoes",
                "rating": None,
                "text": f"Rotten Tomatoes score: {rating['Value']}",
            })
        if rating["Source"] == "Metacritic":
            result["top_reviews"].append({
                "author": "Metacritic",
                "rating": None,
                "text": f"Metacritic score: {rating['Value']}",
            })

    return result


def get_popular_films(page: int = 1) -> list[dict]:
    """
    Curated list of unseen film candidates — mix of recent releases and older classics
    that align with the user's taste profile (female-led, genre-blending, cult favorites).
    """
    candidates = [
        # Recent
        ("Dune: Part Two", 2024),
        ("Poor Things", 2023),
        ("Past Lives", 2023),
        ("Saltburn", 2023),
        ("Priscilla", 2023),
        ("May December", 2023),
        ("All of Us Strangers", 2023),
        ("Challengers", 2024),
        ("I Saw the TV Glow", 2024),
        ("Longlegs", 2024),
        ("Anora", 2024),
        ("Conclave", 2024),
        ("Hard Truths", 2024),
        ("Queer", 2024),
        # Older classics & cult favorites
        ("Booksmart", 2019),
        ("Promising Young Woman", 2020),
        ("Portrait of a Lady on Fire", 2019),
        ("Hereditary", 2018),
        ("The Favourite", 2018),
        ("Lady Bird", 2017),
        ("Get Out", 2017),
        ("Thoroughbreds", 2017),
        ("The Witch", 2015),
        ("Ex Machina", 2014),
        ("Heathers", 1988),
        ("Strange Magic", 2015),
        ("But I'm a Cheerleader", 1999),
        ("Jennifer's Body", 2009),
        ("Scott Pilgrim vs. the World", 2010),
        ("Bring It On", 2000),
        ("10 Things I Hate About You", 1999),
        ("Legally Blonde", 2001),
        ("Mean Girls", 2004),
        ("Pitch Perfect", 2012),
        ("Suspiria", 2018),
        ("Raw", 2016),
        ("Titane", 2021),
        ("Saint Maud", 2019),
        ("Rocketman", 2019),
        ("Bohemian Rhapsody", 2018),
    ]
    return [{"title": t, "year": y} for t, y in candidates]

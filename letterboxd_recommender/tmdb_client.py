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

# Full candidate pool organized by genre/vibe
CANDIDATE_POOL = {
    "horror_thriller": [
        ("Hereditary", 2018), ("The Witch", 2015), ("Ex Machina", 2014),
        ("Longlegs", 2024), ("I Saw the TV Glow", 2024), ("Saint Maud", 2019),
        ("Raw", 2016), ("Titane", 2021), ("Suspiria", 2018),
        ("The Babadook", 2014), ("Nope", 2022), ("Midsommar", 2019),
        ("Jennifer's Body", 2009), ("Thoroughbreds", 2017),
    ],
    "comedy": [
        ("Booksmart", 2019), ("Superbad", 2007), ("Game Night", 2018),
        ("Scott Pilgrim vs. the World", 2010), ("Bridesmaids", 2011),
        ("What We Do in the Shadows", 2014), ("Palm Springs", 2020),
        ("Bring It On", 2000), ("Mean Girls", 2004), ("Pitch Perfect", 2012),
        ("But I'm a Cheerleader", 1999), ("10 Things I Hate About You", 1999),
        ("Legally Blonde", 2001), ("Heathers", 1988),
    ],
    "romance_drama": [
        ("Past Lives", 2023), ("Portrait of a Lady on Fire", 2019),
        ("All of Us Strangers", 2023), ("Challengers", 2024),
        ("Rye Lane", 2023), ("Moonstruck", 1987), ("While You Were Sleeping", 1995),
        ("13 Going on 30", 2004), ("Waiting to Exhale", 1995),
        ("Two Can Play That Game", 2001), ("Silver Linings Playbook", 2012),
        ("When Harry Met Sally...", 1989), ("Drive Me Crazy", 1999),
        ("Uptown Girls", 2003), ("The Broken Hearts Gallery", 2020),
        ("Erin Brockovich", 2000), ("Pretty Woman", 1990),
    ],
    "action_adventure": [
        ("Mad Max: Fury Road", 2015), ("Dune: Part Two", 2024),
        ("The Woman King", 2022), ("Promising Young Woman", 2020),
        ("Kill Bill: Volume 1", 2003), ("Whip It", 2009),
        ("Everything Everywhere All at Once", 2022),
    ],
    "musical_animation": [
        ("Dreamgirls", 2006), ("Rocketman", 2019), ("Sing Street", 2016),
        ("Tick, Tick... Boom!", 2021), ("Funny Girl", 1968),
        ("The Sound of Music", 1965), ("Hairspray", 2007),
        ("The Book of Life", 2014), ("Strange Magic", 2015),
        ("Puss in Boots: The Last Wish", 2022), ("The Wild Robot", 2024),
        ("Turning Red", 2022), ("Encanto", 2021), ("Bohemian Rhapsody", 2018),
    ],
    "prestige_drama": [
        ("Poor Things", 2023), ("Saltburn", 2023), ("Priscilla", 2023),
        ("May December", 2023), ("Anora", 2024), ("The Favourite", 2018),
        ("Conclave", 2024), ("Whiplash", 2014), ("Lady Bird", 2017),
        ("Almost Famous", 2000), ("If Beale Street Could Talk", 2018),
        ("Moonlight", 2016), ("Hard Truths", 2024),
    ],
    "thriller_mystery": [
        ("Knives Out", 2019), ("Glass Onion", 2022), ("Gone Girl", 2014),
        ("The Girl with the Dragon Tattoo", 2011), ("Now You See Me", 2013),
        ("Parasite", 2019), ("Get Out", 2017),
    ],
}

GENRE_CATEGORY_MAP = {
    "horror": "horror_thriller", "thriller": "horror_thriller",
    "comedy": "comedy", "romance": "romance_drama", "drama": "prestige_drama",
    "action": "action_adventure", "adventure": "action_adventure",
    "animation": "musical_animation", "music": "musical_animation",
    "mystery": "thriller_mystery", "crime": "thriller_mystery",
    "sci-fi": "action_adventure", "fantasy": "action_adventure",
}


def _key() -> str:
    key = os.getenv("OMDB_API_KEY")
    if not key:
        raise ValueError("OMDB_API_KEY not set in .env")
    return key


def get_film_data(name: str, year: int | str) -> dict:
    """Fetch film metadata from OMDB by title + year."""
    result = {
        "title": name, "year": year, "genres": [],
        "avg_rating": None, "description": "", "top_reviews": [], "url": "",
    }

    params = {"apikey": _key(), "t": name, "y": str(year), "type": "movie", "plot": "short"}
    resp = requests.get(BASE, params=params, timeout=10)
    time.sleep(DELAY)

    if resp.status_code != 200:
        return result

    data = resp.json()
    if data.get("Response") == "False":
        params.pop("y")
        resp = requests.get(BASE, params=params, timeout=10)
        time.sleep(DELAY)
        data = resp.json()
        if data.get("Response") == "False":
            return result

    result["description"] = data.get("Plot", "")
    result["genres"] = [g.strip() for g in data.get("Genre", "").split(",") if g.strip()]
    result["url"] = f"https://www.imdb.com/title/{data.get('imdbID', '')}/"

    imdb_rating = data.get("imdbRating", "N/A")
    if imdb_rating != "N/A":
        try:
            result["avg_rating"] = round(float(imdb_rating) / 2, 1)
        except ValueError:
            pass

    for rating in data.get("Ratings", []):
        if rating["Source"] in ("Rotten Tomatoes", "Metacritic"):
            result["top_reviews"].append({
                "author": rating["Source"], "rating": None,
                "text": f"{rating['Source']} score: {rating['Value']}",
            })

    return result


def get_popular_films(user_genres: list[str] = None) -> list[dict]:
    """
    Returns a candidate pool tailored to the user's genre preferences.
    user_genres: list of genre strings inferred from the user's top-rated films.
    """
    if not user_genres:
        # Balanced mix across all categories
        seen, result = set(), []
        for films in CANDIDATE_POOL.values():
            for title, year in films[:4]:
                if title not in seen:
                    result.append({"title": title, "year": year})
                    seen.add(title)
        return result

    matched = set()
    for g in user_genres:
        g_lower = g.lower()
        for keyword, category in GENRE_CATEGORY_MAP.items():
            if keyword in g_lower:
                matched.add(category)

    if not matched:
        matched = set(CANDIDATE_POOL.keys())

    seen, result = set(), []
    # Prioritize matched categories, then fill with others
    for category in list(matched) + [c for c in CANDIDATE_POOL if c not in matched]:
        for title, year in CANDIDATE_POOL.get(category, []):
            if title not in seen:
                result.append({"title": title, "year": year})
                seen.add(title)

    return result

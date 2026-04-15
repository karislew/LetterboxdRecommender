"""
AI-powered recommendation engine using Groq (free tier).
Returns structured JSON recommendations.
"""

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def build_film_context(scraped_films: list[dict]) -> str:
    lines = []
    for f in scraped_films:
        lines.append(f"Title: {f['title']} ({f['year']})")
        if f.get("genres"):
            lines.append(f"  Genres: {', '.join(f['genres'])}")
        if f.get("avg_rating"):
            lines.append(f"  IMDb: {f['avg_rating']}/5")
        if f.get("description"):
            lines.append(f"  Plot: {f['description'][:100]}")
        lines.append("")
    return "\n".join(lines)


def get_recommendations(
    user_summary: str,
    scraped_top_films: list[dict],
    scraped_user_films: list[dict],
    favorite_films: list[tuple] = None,
    n: int = 10,
) -> list[dict]:
    """
    Returns a list of recommendation dicts:
    [{ title, year, score, reason }, ...]
    """
    user_film_context = build_film_context(scraped_user_films)
    popular_film_context = build_film_context(scraped_top_films)
    fav_names = ", ".join(name for name, _ in favorite_films if name) if favorite_films else "see profile"

    system_prompt = (
        "You are a film expert and recommendation engine. "
        "Analyze the user's Letterboxd history and return ONLY a JSON array of recommendations. "
        "Each item must have: title (string), year (number), score (number 1-10), reason (string, 2 sentences max). "
        "Prioritize pinned favorites, 5-star films, and liked films as taste signals. "
        "Ensure VARIETY — different genres, decades, tones. No more than 2-3 from the same genre. "
        "Include at least 2 films from before 2000. "
        "You are NOT limited to the candidate list — recommend any film that fits. "
        "Return ONLY valid JSON, no markdown, no explanation outside the array."
    )

    user_prompt = f"""
User's Letterboxd history:
{user_summary}

OMDB metadata for user's top rated + pinned favorites ({fav_names}):
{user_film_context if user_film_context.strip() else "None"}

Candidate unseen films:
{popular_film_context if popular_film_context.strip() else "None"}

Return a JSON array of exactly {n} film recommendations the user hasn't seen.
Avoid films already in their watched list.
Films rated 1-2.5 stars = avoid recommending similar.

Format:
[
  {{"title": "Film Title", "year": 2023, "score": 9, "reason": "2 sentence explanation referencing their specific history."}},
  ...
]
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()

    # Extract JSON array from response
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: return raw as single item
    return [{"title": "Error parsing recommendations", "year": 0, "score": 0, "reason": raw[:200]}]

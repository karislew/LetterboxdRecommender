"""
AI-powered recommendation engine using Groq (free tier).
"""

import os
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
            lines.append(f"  Letterboxd avg rating: {f['avg_rating']}/5")
        if f.get("description"):
            lines.append(f"  Description: {f['description'][:200]}")
        if f.get("top_reviews"):
            lines.append("  Sample community reviews:")
            for r in f["top_reviews"][:3]:
                rating_str = f" ({r['rating']}/5)" if r["rating"] else ""
                lines.append(f"    - {r['author']}{rating_str}: {r['text'][:200]}")
        lines.append("")
    return "\n".join(lines)


def get_recommendations(
    user_summary: str,
    scraped_top_films: list[dict],
    scraped_user_films: list[dict],
    n: int = 10,
) -> str:
    user_film_context = build_film_context(scraped_user_films)
    popular_film_context = build_film_context(scraped_top_films)

    system_prompt = (
        "You are a film expert and recommendation engine. "
        "You analyze a user's Letterboxd history and generate personalized recommendations. "
        "Pay closest attention to: 5-star rated films, liked films (hearted), and highly rated films (4+). "
        "These are the strongest signals of taste. Lower-rated films show what to avoid. "
        "For each recommendation provide a match score out of 10 and explain exactly which "
        "films/patterns from their history informed the score."
    )

    user_prompt = f"""
Here is the user's complete Letterboxd history:

{user_summary}

---

OMDB metadata for the user's top rated films AND their 4 pinned Letterboxd favorites
(Hairspray, The Book of Life, Strange Magic, Guardians of the Galaxy):

{user_film_context if user_film_context.strip() else "No data available."}

---

Candidate films the user has NOT seen yet (mix of recent and older):

{popular_film_context if popular_film_context.strip() else "No data available."}

---

Based on all of the above, recommend {n} films this user would love that they haven't seen yet.

IMPORTANT WEIGHTING:
- The 4 PINNED FAVORITES are the single strongest taste signal — weight these above everything else
- 5-star rated films and liked films are the next strongest signals
- 4 to 4.5 star films are strong secondary signals
- Films rated 1 to 2.5 stars show what to AVOID
- Recommend a MIX of recent films AND older films — don't only suggest new releases
- Do NOT recommend any film already in their watched list

For each recommendation use this exact format:

[NUMBER]. TITLE (YEAR)
Match Score: X/10
Why it fits: 2-3 sentences referencing specific films from their history that informed this recommendation.

Leave a blank line between each recommendation.
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

    return response.choices[0].message.content

"""
BeautifulSoup scraper for Letterboxd.
Fetches: film metadata, average rating, top reviews from a film page.
"""

import time
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

BASE = "https://letterboxd.com"
DELAY = 1.2  # seconds between requests — be polite


def _get(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
        if resp.status_code == 403:
            print(f"  [scraper] Letterboxd blocked the request (403) — skipping scraping.")
        else:
            print(f"  [scraper] HTTP {resp.status_code} for {url}")
    except Exception as e:
        print(f"  [scraper] Error fetching {url}: {e}")
    return None


def film_slug(name: str, year: int | str) -> str:
    """Convert a film name + year to a Letterboxd URL slug guess."""
    slug = re.sub(r"[^a-z0-9\s-]", "", name.lower())
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def scrape_film(name: str, year: int | str, letterboxd_uri: str = "") -> dict:
    """
    Scrape a film page on Letterboxd.
    Returns a dict with: title, year, genres, avg_rating, description, top_reviews.
    Falls back gracefully if anything fails.
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

    # Build the film URL — try slug first, fall back to search
    slug = film_slug(name, year)
    url = f"{BASE}/film/{slug}/"
    soup = _get(url)
    time.sleep(DELAY)

    # If slug didn't work, try search
    if soup is None or soup.find("section", class_="film-header-lockup") is None:
        soup = _search_film(name, year)
        if soup is None:
            return result
        # extract canonical URL from search result
        link = soup.find("a", class_="frame")
        if link:
            url = BASE + link["href"]
            soup = _get(url)
            time.sleep(DELAY)
            if soup is None:
                return result

    result["url"] = url

    # Description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag:
        result["description"] = desc_tag.get("content", "").strip()

    # Genres
    genre_section = soup.find("div", id="tab-genres")
    if genre_section:
        result["genres"] = [a.text.strip() for a in genre_section.find_all("a", class_="text-slug")]

    # Average rating (shown as histogram data attribute)
    rating_tag = soup.find("meta", attrs={"name": "twitter:data2"})
    if rating_tag:
        m = re.search(r"([\d.]+)", rating_tag.get("content", ""))
        if m:
            result["avg_rating"] = float(m.group(1))

    # Top reviews from the film's reviews page
    result["top_reviews"] = _scrape_reviews(url)

    return result


def _search_film(name: str, year: int | str) -> BeautifulSoup | None:
    """Search Letterboxd for a film and return the search results page soup."""
    query = requests.utils.quote(f"{name} {year}")
    url = f"{BASE}/search/films/{query}/"
    return _get(url)


def _scrape_reviews(film_url: str, max_reviews: int = 5) -> list[dict]:
    """
    Scrape the top reviews from a film's reviews page.
    Returns list of dicts with keys: author, rating, text.
    """
    reviews_url = film_url.rstrip("/") + "/reviews/by/activity/"
    soup = _get(reviews_url)
    time.sleep(DELAY)
    if soup is None:
        return []

    reviews = []
    for item in soup.find_all("li", class_="film-detail")[:max_reviews]:
        author_tag = item.find("strong", class_="name")
        author = author_tag.text.strip() if author_tag else "unknown"

        # Rating — encoded as rated-X class (X = 1-10, representing 0.5–5 stars)
        rating = None
        rating_span = item.find("span", class_=re.compile(r"rated-\d+"))
        if rating_span:
            m = re.search(r"rated-(\d+)", " ".join(rating_span.get("class", [])))
            if m:
                rating = int(m.group(1)) / 2  # convert to 0.5–5 scale

        # Review body text
        body_tag = item.find("div", class_="body-text")
        text = ""
        if body_tag:
            # grab visible paragraphs
            paras = body_tag.find_all("p")
            text = " ".join(p.get_text(" ", strip=True) for p in paras)
            text = text[:600]  # cap length

        if text:
            reviews.append({"author": author, "rating": rating, "text": text})

    return reviews


def scrape_popular_films(genre: str = "", page: int = 1) -> list[dict]:
    """
    Scrape the Letterboxd popular films page (optionally filtered by genre).
    Returns a list of dicts with title, year, url.
    """
    if genre:
        url = f"{BASE}/films/popular/genre/{genre}/page/{page}/"
    else:
        url = f"{BASE}/films/popular/page/{page}/"

    soup = _get(url)
    time.sleep(DELAY)
    if soup is None:
        return []

    films = []
    for li in soup.find_all("li", class_=re.compile(r"poster-container")):
        div = li.find("div", class_="film-poster")
        if not div:
            continue
        title = div.get("data-film-name", "").strip()
        year = div.get("data-film-release-year", "").strip()
        slug = div.get("data-film-slug", "").strip()
        if title:
            films.append({
                "title": title,
                "year": year,
                "url": f"{BASE}/film/{slug}/",
                "slug": slug,
            })
    return films

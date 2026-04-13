# Letterboxd AI Movie Recommender

Analyzes your Letterboxd export data, scrapes community reviews from Letterboxd using BeautifulSoup, and uses GPT-4o to generate personalized movie recommendations.

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your OpenAI API key**
   ```bash
   cp .env.example .env
   # edit .env and paste your key
   ```

3. **Run**
   ```bash
   # Full run (scrapes Letterboxd + AI recommendations)
   python main.py

   # Point to a different export folder
   python main.py --export "/path/to/your/letterboxd-export"

   # Skip scraping (faster, uses only your CSV data)
   python main.py --no-scrape

   # Request more recommendations
   python main.py --recs 15
   ```

## How it works

| Step | What happens |
|------|-------------|
| 1 | Reads your exported CSVs: ratings, reviews, diary, watched, liked films |
| 2 | Scrapes Letterboxd film pages for your top-rated films (genres, avg rating, community reviews) |
| 3 | Scrapes the Letterboxd popular films page for unseen films + their community reviews |
| 4 | Sends everything to GPT-4o with a detailed prompt |
| 5 | Prints + saves personalized recommendations with explanations |

## Files

```
letterboxd_recommender/
├── main.py          # Entry point
├── data_loader.py   # Reads and merges your CSV export
├── scraper.py       # BeautifulSoup scraper for Letterboxd
├── recommender.py   # OpenAI prompt builder + API call
├── requirements.txt
└── .env.example
```

## Notes

- The scraper adds a ~1.2s delay between requests to be respectful to Letterboxd's servers.
- No Letterboxd account or API key needed — it scrapes public pages only.
- Recommendations are saved to `recommendations.txt` after each run.

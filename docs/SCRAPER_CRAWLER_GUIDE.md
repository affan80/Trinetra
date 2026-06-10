# Scraper & Crawler Guide

This guide provides step-by-step instructions on how to set up, install dependencies, and run the OSINT (Open Source Intelligence) components of the Trinetra project.

---

## 1. Prerequisites & Dependencies

To run the Trinetra OSINT system, you must have **Python 3.10 or higher** installed. 

### Required Libraries:
The system relies on several key libraries:
*   **Scrapy**: The core engine for crawling and extracting news data.
*   **Requests**: Used for the Reddit API scraper to fetch JSON data.
*   **Python-dateutil**: Used by the common utilities to normalize various date formats.
*   **LXML/Parsel**: Essential for high-performance HTML/XML processing.

These are all listed in the `requirements.txt` file at the project root.

---

## 2. Step-by-Step Setup

### Step 1: Navigate to the Project Root
Open your terminal and enter the project folder:
```bash
cd Trinetra
```

### Step 2: Create a Virtual Environment (Recommended)
This keeps your project dependencies isolated and prevents conflicts.
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

### Step 3: Install Required Dependencies
Install everything required for both the scraper and the crawler:
```bash
pip install -r requirements.txt
```

---

## 3. How to Run the Components

You must set the `PYTHONPATH` to the current directory (`.`) so that the scripts can find the shared packages in `services/common/`.

### A. Running the News Crawler (Spider)
The spider crawls news sites (BBC, Al Jazeera, etc.) and uses a specialized scraper to extract structured article data.

**Command:**
```bash
export PYTHONPATH="."
scrapy runspider services/crawlers/spiders/news_spider.py -o news_results.jsonl
```

*   **Output**: Articles are saved line-by-line in `news_results.jsonl`.
*   **Testing**: Add `-s CLOSESPIDER_ITEMCOUNT=5` to stop after 5 items.

### B. Running the Reddit Scraper
The Reddit scraper monitors specific subreddits (e.g., `r/worldnews`) for keywords like "hack", "cyber", or "attack".

**Command:**
```bash
export PYTHONPATH="."
python services/scraper/surfaceweb/reddit_scraper.py
```

*   **Output**: New posts are printed to the terminal and appended to `reddit_osint.jsonl`.
*   **Persistence**: The script runs in a loop; press `Ctrl+C` to stop it.

---

## 4. Data Output Format

Both tools output data in **JSONL (JSON Lines)** format.

### Example Schema:
```json
{
  "source_name": "aljazeera.com",
  "source_type": "news",
  "url": "https://...",
  "title": "Article Title",
  "text": "Full article body content...",
  "author": "Author Name",
  "published_at": "2026-06-10T12:00:00",
  "metadata": {
    "domain": "aljazeera.com",
    "language": "en"
  }
}
```

---

## 5. Troubleshooting & Maintenance

*   **Import Errors**: If you get a `ModuleNotFoundError`, ensure you ran `export PYTHONPATH="."`.
*   **Rate Limiting**: If Reddit returns a `429 Error`, the script will automatically wait. Do not decrease the `time.sleep()` values.
*   **Shared Logic**: All cleaning and parsing logic is located in `services/common/`. Update these files to change how data is processed across the entire system.

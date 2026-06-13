# Trinetra Scraper & Crawler Guide

This guide helps you run and test the data collection tools in Trinetra.

---

## 1. Quick Start

### Setup
1. **Enter Project Folder**: `cd Trinetra`
2. **Activate Environment**: `source .venv/bin/activate`
3. **Install Tools**: `pip install -r requirements.txt`

### Running the Test Suite
We have a simple script that runs all active spiders (News, Images, Blogs) and saves the results.
```bash
chmod +x run_tests.sh
./run_tests.sh
```
*   **Results**: Check the `test_output/` folder for `.jsonl` files.
*   **Logging**: Spiders now use "Logarithmic Logging" (logs at 1, 2, 4, 8... pages) to keep your terminal clean.

---

## 2. Running Individual Spiders

If you want to run a specific spider manually, use these commands:

### Image Spider (New!)
Finds and extracts images with their titles and descriptions.
```bash
export PYTHONPATH="."
scrapy runspider services/crawlers/spiders/image_spider.py -a urls=https://example.com -o output.jsonl
```

### News Spider
Crawls news sites like BBC or Al Jazeera for articles.
```bash
export PYTHONPATH="."
scrapy runspider services/crawlers/spiders/news_spider.py -a urls=https://www.bbc.com/ -o output.jsonl
```

---

## 3. Adding a New Spider

To add a new spider to the automated test script (`run_tests.sh`):
1. Open `run_tests.sh`.
2. Add your spider path and test URL to the `SPIDERS` list:
   ```bash
   "path/to/your_spider.py|urls=https://test-site.com"
   ```

---

## 4. Tips for Success

*   **Python Path**: Always run `export PYTHONPATH="."` before manual scrapy commands so the system can find its internal parts.
*   **Interruption**: You can stop any crawl by pressing `Ctrl+C`. The data collected up to that point will be saved safely.
*   **Cleaning Data**: All text cleaning and date parsing logic is central in `services/common/`.

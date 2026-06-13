#!/bin/bash

# ==============================================================================
# TRINETRA SCRAPER TEST SUITE
# ==============================================================================
# This script runs all spiders and saves unique output files in test_output/.
# 
# To add a new spider:
# Add a line to the SPIDERS array in the format: "spider_file_path|arguments"
# ==============================================================================

# Configuration
OUTPUT_DIR="test_output"
VENV_PYTHON="./.venv/bin/python3"
SCRAPY="./.venv/bin/scrapy"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
export PYTHONPATH="."

# Ensure output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "📂 Creating output directory: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

# List of spiders to test: "file_path|arguments"
# Note: Arguments can be customized per spider.
SPIDERS=(
    "services/crawlers/spiders/news_spider.py|urls=https://www.bbc.com/"
    "services/crawlers/spiders/image_spider.py|urls=https://books.toscrape.com/"
    "services/crawlers/spiders/blog_spider.py|urls=https://www.csis.org/blogs/"
)

echo "🚀 Starting Trinetra Scraper Tests..."
echo "🕒 Timestamp: $TIMESTAMP"

for ENTRY in "${SPIDERS[@]}"; do
    # Split the entry into path and args
    IFS="|" read -r SPIDER_PATH ARGS <<< "$ENTRY"
    
    # Get just the filename (e.g., news_spider)
    BASENAME=$(basename "$SPIDER_PATH" .py)
    
    # Check if a file for this spider already exists today
    # (Optional logic based on user request: "if file is alrady there dont make new for the out")
    # We use timestamps to ensure "different output in different file" as requested.
    OUT_FILE="${OUTPUT_DIR}/${BASENAME}_${TIMESTAMP}.jsonl"
    
    echo ""
    echo "----------------------------------------------------------------------"
    echo "🕷️  RUNNING: $BASENAME"
    echo "🔗 ARGS: $ARGS"
    echo "📂 OUT:  $OUT_FILE"
    echo "----------------------------------------------------------------------"
    
    # Run the spider with a limit of 10 pages for testing purposes
    $SCRAPY runspider "$SPIDER_PATH" \
        -a $ARGS \
        -a max_pages=10 \
        -o "$OUT_FILE" \
        --loglevel INFO
    
    if [ $? -eq 0 ]; then
        COUNT=$(wc -l < "$OUT_FILE" | xargs)
        echo "✅ SUCCESS: $BASENAME completed. Scraped $COUNT items."
    else
        echo "❌ ERROR: $BASENAME failed. Check logs above."
    fi
done

echo ""
echo "======================================================================"
echo "🎉 TEST SUITE FINISHED"
echo "📂 All results saved in: $OUTPUT_DIR"
echo "======================================================================"

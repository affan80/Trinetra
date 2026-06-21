# Trinetra: Intelligent OSINT for the Modern Age 👁️

Trinetra is an India-focused AI platform built for the **Indian Air Force**. It takes scattered public data—news, social media, images, and videos—and turns it into clear, verified, and linked intelligence.

Instead of just giving you a list of links, Trinetra builds an **Intelligence Graph**. It connects the dots between people, places, claims, and media so you can see the full story, not just the fragments.

---

## What Trinetra Does for You

*   **Verifies Information**: Automatically checks if a source is credible or if a piece of media is fake.
*   **Connects the Dots**: Links related posts, events, and locations into a single "Intelligence Graph."
*   **Monitors Social Media**: Tracks how stories spread and identifies who is behind coordinated campaigns.
*   **Maps Everything**: Visualizes events and claims on a map so you have instant situational awareness.
*   **Speaks the Language**: Handles English, Hindi, and regional languages to cover all of India's information space.
*   **Entity Intelligence**: Automatically extracts people, organizations, and locations from text using advanced NLP.
*   **Ready-to-Use Reports**: Generates daily briefs and incident reports so you can make decisions immediately.

---

## Setting up NER Intelligence

To enable the new Named Entity Recognition (NER) pipeline:

1.  **Install dependencies** (included in `requirements.txt`):
    ```bash
    pip install -r requirements.txt
    ```
2.  **Download the Spacy English model**:
    ```bash
    python -m spacy download en_core_web_sm
    ```
    *If not installed, the NER pipeline will gracefully skip processing without impacting the crawl.*

---

## Key Dimensions of Intelligence

Trinetra is built on these foundational dimensions to ensure public data is transformed into actionable intelligence:

| Dimension | Meaning for Trinetra | Why it Matters |
| :--- | :--- | :--- |
| **Multi-source Ingestion** | Collect public data from news, RSS, web, social media, video, images, and public datasets. | OSINT value depends on coverage across fragmented public sources. |
| **Credibility Scoring** | Score source reliability, claim confidence, media authenticity, and misinformation risk. | Prevents raw collection from becoming unverified noise. |
| **Intelligence Graph** | Connect sources, claims, entities, events, locations, media, narratives, and evidence. | Allows analysts to investigate relationships and chains of evidence. |
| **Real-time Alerting** | Detect emerging events and narrative spikes quickly. | Information warfare and crises move faster than manual monitoring cycles. |
| **Social Media Intelligence** | Track hashtags, influencer nodes, amplification patterns, and coordinated campaigns. | Narratives often emerge on social platforms before formal reporting. |
| **Multilingual Monitoring** | Handle Hindi, English, regional Indian languages, and adversarial foreign languages. | India-focused OSINT requires language coverage beyond English. |
| **Multimodal Analysis** | Analyze text, image, video, audio, OCR, ASR, and metadata. | Modern misinformation is often visual or cross-media. |
| **Geospatial Intelligence** | Map events, claims, source origins, and heatmaps. | Defence users need location-first situational awareness. |
| **Timeline Analysis** | Reconstruct first-seen time, amplification timeline, and event progression. | Temporal order is critical for verifying claims and identifying origins. |
| **Analyst Workflow** | Support case folders, notes, review queues, evidence boards, and escalation. | AI outputs must fit intelligence workflows. |
| **Report Generation** | Generate daily briefs, incident reports, source reliability reports, and misinformation reports. | Analysts need decision-ready outputs, not just dashboards. |

---

## Quick Start (Using Docker)

The easiest way to get Trinetra running is with **Docker**.

### 1. Setup
*   Clone this folder to your computer.
*   Create a file named `.env` in the main folder and add these lines:
    ```env
    REDIS_URL=redis://redis:6379/0
    TELEGRAM_API_ID=your_id_here
    TELEGRAM_API_HASH=your_hash_here
    ```

### 2. Start the System
Open your terminal in the project folder and run:
```bash
docker compose up -d --build
```
*This starts the Database (Redis), the API, and the background Workers.*

### 3. Start Scraping Data
You can run all the data collectors (spiders) at once:
```bash
docker compose --profile crawlers up
```

---

## Running Locally (Without Docker)

If you prefer to run it directly on your machine:

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run the test script**:
    This will start all scrapers in parallel and connect to your Redis:
    ```bash
    bash run_tests.sh
    ```

---

## How to Monitor

*   **Live Stats**: Open [http://localhost:8000/stats](http://localhost:8000/stats) in your browser.
*   **System Logs**: Run `docker compose logs -f` to see what's happening under the hood.

---

**Trinetra** is about moving from "searching for data" to "understanding intelligence." 🇮🇳

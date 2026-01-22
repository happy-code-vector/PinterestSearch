# Pinterest Multi-Topic Scraper

Scrape Pinterest images across 300+ aesthetic topics organized by category with built-in NSFW filtering.

## Features

- **Multi-topic batch processing** - Scrape all 300+ topics or specific categories
- **Category organization** - Downloads organized by category and topic
- **Duplicate detection** - Prevents collecting the same pins across topics
- **NSFW text filtering** - Blocks inappropriate content based on keywords
- **Concurrent processing** - Multiple topics scraped simultaneously
- **Progress tracking** - Real-time logging and progress updates
- **Environment-based config** - Settings via `.env` file
- **Human-like behavior** - Random delays and mouse movements to avoid detection

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

4. Copy environment template:
```bash
cp .env.example .env
```

5. Edit `.env` with your settings

## Configuration

Edit `.env` file to configure:

| Setting | Description | Default |
|---------|-------------|---------|
| `CATEGORIES` | Categories to scrape (comma-separated or "ALL") | ALL |
| `MAX_PINS_PER_TOPIC` | Maximum pins to collect per topic | 100 |
| `OUTPUT_FOLDER` | Output directory for downloads | pinterest_downloads |
| `DOWNLOAD_IMAGES` | Download images (true/false) | true |
| `HEADLESS` | Run browser in headless mode (true/false) | true |
| `TIMEOUT_MS` | Page load timeout in milliseconds | 45000 |
| `PROXY` | Optional proxy URL | empty |
| `MAX_CONCURRENT_TOPICS` | Topics to process simultaneously | 3 |
| `MAX_CONCURRENT_DOWNLOADS` | Image downloads simultaneously | 10 |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |

## Usage

### Scrape All Categories
```bash
python main.py
```

With `.env`:
```
CATEGORIES=ALL
```

### Scrape Specific Categories
Edit `.env`:
```
CATEGORIES=STUDY/ACADEMIA,FOOD/COOKING,BOOKS/READING
```

Or use comma-separated:
```
CATEGORIES=STUDY_ACADEMIA,FOOD_COOKING,BOOKS_READING
```

### Run with Different Pin Limits
Edit `.env`:
```
MAX_PINS_PER_TOPIC=50
```

## Categories

| Category | Topics |
|----------|--------|
| STUDY_ACADEMIA | dark academia, study motivation, desk organization... |
| FOOD_COOKING | smoothie bowl, matcha aesthetic, baking aesthetic... |
| BOOKS_READING | bookstok, reading nook, bookshelf aesthetic... |
| TRAVEL | European summer, coastal grandmother, Paris aesthetic... |
| FITNESS_WELLNESS | clean girl aesthetic, pilates princess, gym aesthetic... |
| NATURE_OUTDOORS | cottage core, forest bathing, hiking aesthetic... |
| HOME_LIFESTYLE | clean girl morning, morning routine, that girl aesthetic... |
| FASHION_STYLE | clean girl, coquette aesthetic, balletcore... |
| ART_CULTURE | museum aesthetic, art gallery, classical paintings... |
| COFFEE_CAFE | coffee shop aesthetic, latte art, cafe hopping... |
| PRODUCTIVITY_ORGANIZATION | productive day, planner aesthetic, desk setup... |
| COZY_COMFORT | rainy day aesthetic, cozy corner, blanket fort... |
| BEAUTY_SKINCARE | clean beauty, skincare routine, glass skin... |
| VINTAGE_NOSTALGIA | vintage aesthetic, film photography, thrift haul... |
| SEASONS_HOLIDAYS | autumn aesthetic, fall vibes, winter wonderland... |
| JOURNALING_WRITING | journaling aesthetic, morning pages, creative writing... |
| MUSIC_CREATIVE | vinyl collection, record player, music aesthetic... |
| COUPLE | couple aesthetic |

View all topics in [topics.py](topics.py).

## Output Structure

```
pinterest_downloads/
├── all_pins.json                    # Master JSON with all pins
├── STUDY_ACADEMIA/
│   ├── dark_academia/
│   │   ├── images/
│   │   │   ├── 123456789.jpg
│   │   │   └── ...
│   │   └── dark_academia_pins.json  # Per-topic metadata
│   ├── light_academia/
│   │   └── ...
│   └── ...
├── FOOD_COOKING/
│   └── ...
└── ...
```

## NSFW Filtering

### Text-Based Filtering (Default)
The scraper filters out pins with NSFW keywords in title/description:
- nude, naked, sexy, hot, adult, porn, xxx, erotic, 18+, onlyfans
- bikini, lingerie, booty, ass, tits, boobs, cleavage, thong
- sex, topless, underwear, braless, see-through, explicit, fetish

### Image-Based Filtering (Optional)
For enhanced NSFW detection using AI:

1. Install additional dependencies:
```bash
pip install tensorflow nudenet Pillow
```

2. Enable in `.env`:
```
USE_NSFW_DETECTOR=true
NSFW_THRESHOLD=0.7
```

## Logging

Logs are saved to `pinterest_scraper.log` and printed to console:
```
2026-01-22 10:30:15 [INFO] Starting scrape: [STUDY_ACADEMIA] dark academia
2026-01-22 10:30:45 [INFO] Progress: 1/321 topics | Total pins: 100 | Latest: [STUDY_ACADEMIA] dark academia (100 pins)
```

## Troubleshooting

### Slow Scrolling
Pinterest may rate-limit. Reduce concurrent topics:
```
MAX_CONCURRENT_TOPICS=1
```

### Missing Images
Some images may fail to download. Check logs for details.

### Login Required
If Pinterest requires login, set `HEADLESS=false` and log in manually.

## Requirements

- Python 3.10+
- Playwright
- aiohttp
- python-dotenv

## License

Use responsibly. Respect Pinterest's Terms of Service.

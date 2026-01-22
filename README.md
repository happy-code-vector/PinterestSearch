# Pinterest Multi-Topic Scraper

Scrape Pinterest images across 300+ aesthetic topics organized by category with built-in NSFW filtering.

## Features

- **Multi-topic batch processing** - Scrape all 300+ topics or specific categories
- **Category organization** - Downloads organized by category and topic
- **Google Drive upload** - Automatic upload to your Google Drive folder
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

6. (Optional) For Google Drive upload, see [Google Drive Setup](#google-drive-upload)

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
| `ENABLE_DRIVE_UPLOAD` | Upload to Google Drive after scraping | false |
| `DRIVE_FOLDER_URL` | Google Drive folder URL | empty |
| `USE_NSFW_DETECTOR` | Enable AI image NSFW detection | false |
| `NSFW_BACKEND` | Detection backend (nudenet/pytorch) | nudenet |
| `NSFW_THRESHOLD` | NSFW threshold (0.0-1.0) | 0.7 |

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

### Run on Google Colab (Recommended)

**Benefits:**
- Free GPU/Compute resources
- Direct Google Drive integration (no OAuth needed)
- Runs in cloud (can close browser while scraping)

1. Open [Pinterest_Scraper_Colab.ipynb](Pinterest_Scraper_Colab.ipynb) in Google Colab
2. Run each cell in order
3. Configure scraping preferences in the settings cell
4. Content saves directly to your Google Drive

The notebook includes interactive controls for:
- Category selection
- Pins per topic
- Output path in Google Drive
- Concurrency settings

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

The scraper includes two layers of NSFW protection:

### 1. Text-Based Filtering (Always Active)
Filters out pins with NSFW keywords in title/description:
- nude, naked, sexy, hot, adult, porn, xxx, erotic, 18+, onlyfans
- bikini, lingerie, booty, ass, tits, boobs, cleavage, thong
- sex, topless, underwear, braless, see-through, explicit, fetish

### 2. Image-Based AI Detection (Optional)

**Available Backends:**

| Backend | Pros | Cons | Best For |
|---------|------|------|----------|
| **NudeNet** | Lightweight (20MB), fast (0.1-0.3s/image), no heavy dependencies | May miss some edge cases | Google Colab, CPU, general use |
| **PyTorch** | More accurate with proper model, GPU support | Heavy (500MB+), requires PyTorch, complex setup | Production, GPU available |

**Installation:**

**Option A: NudeNet (Recommended)**
```bash
pip install nudenet==3.4.2
```

**Option B: PyTorch**
```bash
pip install torch==2.1.0 torchvision==0.16.0 Pillow==11.1.0
```

**Configuration (.env):**
```
USE_NSFW_DETECTOR=true
NSFW_BACKEND=nudenet
NSFW_THRESHOLD=0.7
```

**Threshold Guide:**
- `0.5` - Balanced filtering
- `0.7` - Recommended (fewer false positives)
- `0.9` - Very strict (may filter safe content)

**How It Works:**
1. Images are downloaded first
2. AI detector scans each downloaded image
3. NSFW images are automatically deleted
4. Logs show how many images were filtered per topic

**Example Output:**
```
[INFO] NSFW filtering enabled: NudeNet
[INFO] Downloaded 50/50 images for [STUDY_ACADEMIA] dark_academia
[INFO] NSFW filter: Removed 2/50 images for [STUDY_ACADEMIA] dark_academia
```

**Note:** For PyTorch backend, the default implementation uses a generic ResNet50 model. For production use with actual NSFW detection, you would need a model trained on NSFW datasets. NudeNet is recommended as it's purpose-built for this task.

## Google Drive Upload

Automatically upload scraped content to Google Drive with proper folder structure.

### Setup Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Drive API:
   - Search for "Google Drive API" and enable it
4. Create OAuth credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Download the credentials JSON file
5. Rename the downloaded file to `credentials.json` and place it in the project root

### Enable Upload

Edit `.env`:
```
ENABLE_DRIVE_UPLOAD=true
DRIVE_FOLDER_URL=https://drive.google.com/drive/folders/1C9WuerzHjYkV5gka6EsB1p9_1bRlAPZy
```

### Drive Folder Structure

Content is uploaded with the same structure as local folders:
```
Google Drive Folder (your target)
├── STUDY_ACADEMIA/
│   ├── dark_academia/
│   │   ├── images/
│   │   │   ├── 123456789.jpg
│   │   │   └── ...
│   │   └── dark_academia_pins.json
│   ├── light_academia/
│   │   └── ...
│   └── ...
├── FOOD_COOKING/
│   └── ...
└── ...
```

### First Run

When you run the scraper with Google Drive enabled for the first time:
1. A browser window will open
2. Sign in to your Google account
3. Grant permission to access Google Drive
4. The token is saved automatically for future runs

### Upload Only (Skip Scraping)

To upload existing local content without scraping:
```python
from drive_uploader import DriveUploader, get_folder_id_from_url
from pathlib import Path

uploader = DriveUploader()
if uploader.authenticate():
    folder_id = get_folder_id_from_url("your_folder_url")
    results = uploader.upload_all(Path("pinterest_downloads"), folder_id)
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
- playwright
- aiohttp
- python-dotenv

### Optional (for Google Drive upload)
- google-api-python-client
- google-auth-oauthlib
- google-auth

### Optional (for NSFW image detection)
Choose one:
- **NudeNet (Recommended):** nudenet
- **PyTorch:** torch, torchvision, Pillow

## License

Use responsibly. Respect Pinterest's Terms of Service.

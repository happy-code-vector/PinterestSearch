"""
Pinterest Multi-Topic Scraper
Scrapes Pinterest images across multiple aesthetic topics with NSFW filtering.
"""

import asyncio
import random
import json
import os
import logging
import hashlib
from pathlib import Path
from typing import Set, List, Dict, Tuple
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import aiohttp
from dotenv import load_dotenv

from topics import get_all_topics, get_topics_for_categories
from drive_uploader import DriveUploader, get_folder_id_from_url
from nsfw_filter import NSFWDetector

load_dotenv()

CONFIG = {
    "categories": os.getenv("CATEGORIES", "ALL"),
    "max_pins_per_topic": int(os.getenv("MAX_PINS_PER_TOPIC", "100")),
    "output_folder": os.getenv("OUTPUT_FOLDER", "pinterest_downloads"),
    "download_images": os.getenv("DOWNLOAD_IMAGES", "true").lower() == "true",
    "headless": os.getenv("HEADLESS", "true").lower() == "true",
    "timeout": int(os.getenv("TIMEOUT_MS", "45000")),
    "proxy": os.getenv("PROXY", None) or None,
    "use_nsfw_detector": os.getenv("USE_NSFW_DETECTOR", "false").lower() == "true",
    "nsfw_threshold": float(os.getenv("NSFW_THRESHOLD", "0.7")),
    "max_concurrent_topics": int(os.getenv("MAX_CONCURRENT_TOPICS", "3")),
    "max_concurrent_downloads": int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "10")),
    "log_level": os.getenv("LOG_LEVEL", "INFO"),
    "enable_drive_upload": os.getenv("ENABLE_DRIVE_UPLOAD", "false").lower() == "true",
    "drive_folder_url": os.getenv("DRIVE_FOLDER_URL", ""),
}

NSFW_BLOCKLIST = [
    "nude", "naked", "sexy", "hot", "adult", "porn", "xxx", "erotic", "18+", "onlyfans",
    "bikini", "lingerie", "booty", "ass", "tits", "boobs", "cleavage", "thong", "nsfw",
    "sex", "topless", "underwear", "braless", "see-through", "explicit", "fetish",
]

def setup_logging():
    """Configure logging based on LOG_LEVEL."""
    log_level = getattr(logging, CONFIG["log_level"].upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("pinterest_scraper.log", encoding="utf-8")
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def is_text_safe(title: str, description: str) -> bool:
    """Check if pin text is safe (no NSFW keywords)."""
    text = (title + " " + description).lower()
    return not any(kw in text for kw in NSFW_BLOCKLIST)

def get_pin_hash(pin_id: str) -> str:
    """Generate hash for deduplication."""
    return hashlib.md5(pin_id.encode()).hexdigest()[:16]

async def download_images_batch(pins: List[Dict], category: str, topic: str, output_base: Path):
    """Download multiple images concurrently with NSFW filtering on full-resolution images."""
    if not CONFIG["download_images"]:
        return

    images_dir = output_base / category / topic.replace(" ", "_") / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(CONFIG["max_concurrent_downloads"])

    # Initialize NSFW detector once if enabled
    nsfw_detector = None
    if CONFIG["use_nsfw_detector"]:
        try:
            nsfw_detector = NSFWDetector(threshold=CONFIG["nsfw_threshold"])
            logger.info(f"NSFW filtering enabled: {nsfw_detector.get_backend_name()}")
        except ImportError as e:
            logger.error(f"Failed to initialize NSFW detector: {e}")
            logger.info("Proceeding without NSFW image detection")

    async def download_with_semaphore(session: aiohttp.ClientSession, pin: Dict):
        async with semaphore:
            img_filename = f"{pin['pin_id']}.jpg"
            img_path = images_dir / img_filename

            if img_path.exists():
                return {"path": img_path, "success": True, "skipped": False}

            # Download full resolution image to memory first
            full_url = pin["image_url"].replace("236x", "originals").replace("564x", "originals")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.pinterest.com/'
            }

            try:
                async with session.get(full_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.debug(f"Failed to download {img_filename}: HTTP {response.status}")
                        return {"path": img_path, "success": False, "skipped": False}

                    # Read full image bytes into memory
                    image_bytes = await response.read()

                    # Check NSFW on the actual full-resolution image before saving
                    if nsfw_detector:
                        try:
                            is_nsfw = await asyncio.get_event_loop().run_in_executor(
                                None, nsfw_detector.is_nsfw_from_bytes, image_bytes
                            )

                            if is_nsfw:
                                logger.debug(f"Filtered NSFW image (full-resolution): {img_filename}")
                                return {"path": img_path, "success": False, "skipped": "NSFW"}
                        except Exception as e:
                            logger.debug(f"NSFW check failed for {img_filename}: {e}")
                            # Continue with save if check fails

                    # Save the image to disk only after passing NSFW check
                    img_path.write_bytes(image_bytes)
                    logger.debug(f"Downloaded: {img_filename}")
                    return {"path": img_path, "success": True, "skipped": False}

            except Exception as e:
                logger.debug(f"Failed: {img_filename} - {e}")
                return {"path": img_path, "success": False, "skipped": False}

    # Use session properly
    async with aiohttp.ClientSession() as session:
        tasks = [download_with_semaphore(session, pin) for pin in pins]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        nsfw_filtered = sum(1 for r in results if isinstance(r, dict) and r.get("skipped") == "NSFW")

        logger.info(f"Downloaded {success_count}/{len(pins)} images for [{category}] {topic}")

        if nsfw_filtered > 0:
            logger.info(f"NSFW filter: Skipped {nsfw_filtered}/{len(pins)} images for [{category}] {topic}")

async def human_like_scroll(page):
    """Smooth human-like scrolling."""
    viewport_height = page.viewport_size["height"]
    for _ in range(random.randint(2, 5)):
        scroll_distance = random.randint(300, viewport_height - 200)
        await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        await asyncio.sleep(random.uniform(0.8, 2.2))

async def random_mouse_move(page):
    """Random mouse movements to look more human."""
    viewport = page.viewport_size
    x = random.randint(100, viewport["width"] - 100)
    y = random.randint(100, viewport["height"] - 100)
    await page.mouse.move(x, y, steps=random.randint(8, 15))
    await asyncio.sleep(random.uniform(0.3, 1.0))

async def random_delay(min_sec: float = 1.8, max_sec: float = 4.2):
    """Random delay to mimic human behavior."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def scrape_topic(
    category: str,
    topic: str,
    collected_hashes: Set[str],
    _output_base: Path,
    progress_callback = None,
    max_retries: int = 3
) -> List[Dict]:
    """
    Scrape Pinterest for a single topic.

    Args:
        category: Category name (e.g., "STUDY_ACADEMIA")
        topic: Topic keyword to search
        collected_hashes: Set of already collected pin hashes (for deduplication)
        output_base: Base output directory
        progress_callback: Optional callback for progress updates

    Returns:
        List of collected pin data
    """
    logger.info(f"Starting scrape: [{category}] {topic}")
    collected_pins = []

    for attempt in range(max_retries):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=CONFIG["headless"],
                    proxy={"server": CONFIG["proxy"]} if CONFIG["proxy"] else None,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor"
                    ]
                )

                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York",
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    }
                )

                # Add stealth script
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    
                    window.chrome = {
                        runtime: {},
                    };
                """)

                page = await context.new_page()
                
                # Additional stealth measures
                await page.evaluate("""
                    delete navigator.__proto__.webdriver;
                """)

                # Go to Pinterest homepage first to establish session
                await page.goto("https://www.pinterest.com", wait_until="domcontentloaded", timeout=CONFIG["timeout"])
                await random_delay(2, 4)

                # Go to search page
                search_url = f"https://www.pinterest.com/search/pins/?q={topic.replace(' ', '%20')}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=CONFIG["timeout"])

                try:
                    # Accept cookies if popup appears
                    try:
                        await page.get_by_role("button", name="Accept all").click(timeout=8000)
                    except:
                        pass

                    last_height = await page.evaluate("document.body.scrollHeight")
                    scroll_attempts = 0
                    max_scrolls = 50

                    while len(collected_pins) < CONFIG["max_pins_per_topic"] and scroll_attempts < max_scrolls:
                        await human_like_scroll(page)
                        await random_mouse_move(page)
                        await random_delay()

                        # Get current pin elements
                        pin_elements = await page.query_selector_all('div[data-test-id="pin"]')

                        for pin_el in pin_elements:
                            if len(collected_pins) >= CONFIG["max_pins_per_topic"]:
                                break

                            try:
                                # Extract pin data
                                title_el = await pin_el.query_selector('div[data-test-id="pin-title"]')
                                title = await title_el.inner_text() if title_el else ""
                                title = title.strip()

                                desc_el = await pin_el.query_selector('div[data-test-id="pin-description"]')
                                description = await desc_el.inner_text() if desc_el else ""
                                description = description.strip()

                                img_el = await pin_el.query_selector('img[src*="pinimg.com"]')
                                img_src = await img_el.get_attribute("src") if img_el else None

                                link_el = await pin_el.query_selector('a[href*="/pin/"]')
                                pin_url = await link_el.get_attribute("href") if link_el else ""
                                pin_id = pin_url.split("/pin/")[-1].split("/")[0] if pin_url else ""

                                if img_src and pin_id:
                                    pin_hash = get_pin_hash(pin_id)

                                    # Check duplicates
                                    if pin_hash in collected_hashes:
                                        continue

                                    # Safety check
                                    if not is_text_safe(title, description):
                                        logger.debug(f"Filtered NSFW pin: {title[:50]}")
                                        continue

                                    pin_data = {
                                        "pin_id": pin_id,
                                        "title": title,
                                        "description": description,
                                        "image_url": img_src,
                                        "pin_url": f"https://www.pinterest.com{pin_url}" if pin_url else "",
                                        "category": category,
                                        "topic": topic,
                                        "scraped_at": datetime.now().isoformat(),
                                    }

                                    collected_pins.append(pin_data)
                                    collected_hashes.add(pin_hash)

                                    if progress_callback:
                                        progress_callback(category, topic, len(collected_pins))

                                    logger.debug(f"[{category}] {topic}: Found pin {len(collected_pins)}")

                            except Exception as e:
                                logger.debug(f"Error processing pin element: {e}")
                                continue

                        # Check if we stopped loading new content
                        new_height = await page.evaluate("document.body.scrollHeight")
                        if new_height == last_height:
                            scroll_attempts += 1
                        else:
                            scroll_attempts = 0
                            last_height = new_height

                        if len(collected_pins) >= CONFIG["max_pins_per_topic"]:
                            break

                except Exception as e:
                    logger.error(f"Error during scraping [{category}] {topic}: {e}")

                finally:
                    await browser.close()

                # If we got pins, break out of retry loop
                if collected_pins:
                    break

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed for [{category}] {topic}: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed for [{category}] {topic}")

    return collected_pins

class ProgressTracker:
    """Track and display scraping progress."""
    def __init__(self, total_topics: int):
        self.total_topics = total_topics
        self.completed_topics = 0
        self.total_pins = 0
        self.category_progress: Dict[str, int] = {}

    def update(self, category: str, _topic: str, pin_count: int):
        """Update progress for a topic."""
        if category not in self.category_progress:
            self.category_progress[category] = 0
        self.category_progress[category] += pin_count
        self.total_pins += pin_count

    def complete_topic(self, category: str, topic: str, pin_count: int):
        """Mark a topic as completed."""
        self.completed_topics += 1
        self.update(category, topic, pin_count)
        logger.info(
            f"Progress: {self.completed_topics}/{self.total_topics} topics | "
            f"Total pins: {self.total_pins} | "
            f"Latest: [{category}] {topic} ({pin_count} pins)"
        )

async def scrape_all_topics():
    """Scrape all topics according to configuration."""
    # Determine which categories to process
    if CONFIG["categories"].upper() == "ALL":
        topics_to_scrape = get_all_topics()
        logger.info(f"Scraping ALL categories - {len(topics_to_scrape)} total topics")
    else:
        category_list = [c.strip().upper().replace("/", "_") for c in CONFIG["categories"].split(",")]
        topics_to_scrape = get_topics_for_categories(category_list)
        logger.info(f"Scraping {len(category_list)} categories - {len(topics_to_scrape)} total topics")

    # Setup output directory
    output_base = Path(CONFIG["output_folder"])
    output_base.mkdir(exist_ok=True)

    # Track duplicates across all topics
    collected_hashes: Set[str] = set()

    # Track progress
    tracker = ProgressTracker(len(topics_to_scrape))

    # Store all collected pins
    all_pins = []

    # Process topics in batches
    semaphore = asyncio.Semaphore(CONFIG["max_concurrent_topics"])

    async def scrape_with_limit(category_topic: Tuple[str, str]):
        category, topic = category_topic

        async with semaphore:
            pins = await scrape_topic(
                category,
                topic,
                collected_hashes,
                output_base,
                progress_callback=None  # Can add callback for real-time updates
            )

            if pins:
                # Save category/topic JSON
                topic_dir = output_base / category / topic.replace(" ", "_")
                topic_dir.mkdir(parents=True, exist_ok=True)

                json_path = topic_dir / f"{topic.replace(' ', '_')}_pins.json"
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(pins, f, indent=2, ensure_ascii=False)

                # Download images
                await download_images_batch(pins, category, topic, output_base)

                tracker.complete_topic(category, topic, len(pins))
                all_pins.extend(pins)
            else:
                logger.warning(f"No pins collected for [{category}] {topic}")

            # Random delay between topics
            await random_delay(3, 8)

    # Run all topic scrapers
    tasks = [scrape_with_limit(ct) for ct in topics_to_scrape]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Save master JSON with all pins
    master_json = output_base / "all_pins.json"
    with open(master_json, "w", encoding="utf-8") as f:
        json.dump(all_pins, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*60}")
    logger.info(f"Scraping complete!")
    logger.info(f"Total topics processed: {tracker.completed_topics}/{tracker.total_topics}")
    logger.info(f"Total unique pins collected: {tracker.total_pins}")
    logger.info(f"Master JSON saved to: {master_json}")
    logger.info(f"{'='*60}\n")

    # Print category breakdown
    logger.info("Pins per category:")
    for category, count in sorted(tracker.category_progress.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {category}: {count} pins")

    # Upload to Google Drive if enabled
    if CONFIG["enable_drive_upload"] and CONFIG["drive_folder_url"]:
        logger.info("\n" + "="*60)
        logger.info("Starting Google Drive upload...")
        logger.info("="*60)

        try:
            uploader = DriveUploader()

            if uploader.authenticate():
                folder_id = get_folder_id_from_url(CONFIG["drive_folder_url"])
                logger.info(f"Target folder ID: {folder_id}")

                results = uploader.upload_all(output_base, folder_id)

                # Print upload results
                success_count = sum(1 for v in results.values() if v)
                fail_count = len(results) - success_count

                logger.info(f"\n{'='*60}")
                logger.info(f"Upload complete: {success_count} succeeded, {fail_count} failed")
                logger.info(f"{'='*60}\n")

                for category, success in results.items():
                    status = "✓" if success else "✗"
                    logger.info(f"  {status} {category}")
            else:
                logger.error("Failed to authenticate with Google Drive")
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}")
    elif CONFIG["enable_drive_upload"]:
        logger.warning("Google Drive upload enabled but DRIVE_FOLDER_URL not set")
    else:
        logger.info("\nGoogle Drive upload disabled (set ENABLE_DRIVE_UPLOAD=true to enable)")

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Pinterest Multi-Topic Scraper")
    logger.info("="*60)
    logger.info(f"Configuration:")
    logger.info(f"  Categories: {CONFIG['categories']}")
    logger.info(f"  Max pins per topic: {CONFIG['max_pins_per_topic']}")
    logger.info(f"  Download images: {CONFIG['download_images']}")
    logger.info(f"  Headless: {CONFIG['headless']}")
    logger.info(f"  Concurrent topics: {CONFIG['max_concurrent_topics']}")
    logger.info("="*60 + "\n")

    asyncio.run(scrape_all_topics())

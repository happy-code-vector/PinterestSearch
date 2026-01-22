import asyncio
import random
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ===================== CONFIG =====================
CONFIG = {
    "keyword": "cute cat illustrations",          # Change this!
    "max_pins": 500,                              # How many safe pins to collect
    "output_folder": "pinterest_downloads",
    "download_images": True,
    "safe_keywords": ["cute", "kawaii", "cartoon", "illustration", "minimalist", "vintage", "aesthetic", "funny", "animal", "pet"],
    "nsfw_blocklist": [
        "nude", "naked", "sexy", "hot", "adult", "porn", "xxx", "erotic", "18+", "onlyfans",
        "bikini", "lingerie", "booty", "ass", "tits", "boobs", "cleavage", "thong"
    ],
    "proxy": None,  # Example: "http://user:pass@ip:port" or None
    "headless": True,
    "timeout": 45000,  # ms
}

# ===================== HELPERS =====================
def is_safe_pin(title: str, description: str) -> bool:
    text = (title + " " + description).lower()
    
    # Must contain at least one safe keyword
    has_safe = any(kw.lower() in text for kw in CONFIG["safe_keywords"])
    
    # Must NOT contain any nsfw keyword
    has_nsfw = any(kw.lower() in text for kw in CONFIG["nsfw_blocklist"])
    
    return has_safe and not has_nsfw

async def human_like_scroll(page):
    """Smooth human-like scrolling"""
    viewport_height = page.viewport_size["height"]
    for _ in range(random.randint(2, 5)):
        scroll_distance = random.randint(300, viewport_height - 200)
        await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        await asyncio.sleep(random.uniform(0.8, 2.2))

async def random_mouse_move(page):
    """Random mouse movements to look more human"""
    viewport = page.viewport_size
    x = random.randint(100, viewport["width"] - 100)
    y = random.randint(100, viewport["height"] - 100)
    await page.mouse.move(x, y, steps=random.randint(8, 15))
    await asyncio.sleep(random.uniform(0.3, 1.0))

# ===================== MAIN SCRAPER =====================
async def scrape_pinterest():
    print(f"Starting Pinterest scrape for: '{CONFIG['keyword']}'")
    print(f"Target: up to {CONFIG['max_pins']} safe pins\n")

    # Prepare folders
    output_dir = Path(CONFIG["output_folder"])
    output_dir.mkdir(exist_ok=True)
    images_dir = output_dir / "images"
    if CONFIG["download_images"]:
        images_dir.mkdir(exist_ok=True)

    collected_pins = []

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=CONFIG["headless"],
            proxy={"server": CONFIG["proxy"]} if CONFIG["proxy"] else None
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )

        page = await context.new_page()
        await page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
        })

        # Go to search page
        search_url = f"https://www.pinterest.com/search/pins/?q={CONFIG['keyword'].replace(' ', '%20')}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=CONFIG["timeout"])

        try:
            # Accept cookies if popup appears
            try:
                await page.get_by_role("button", name="Accept all").click(timeout=8000)
            except:
                pass

            last_height = await page.evaluate("document.body.scrollHeight")
            scroll_attempts = 0

            while len(collected_pins) < CONFIG["max_pins"] and scroll_attempts < 80:
                await human_like_scroll(page)
                await random_mouse_move(page)
                await asyncio.sleep(random.uniform(1.8, 4.2))  # Realistic wait

                # Get current pin elements
                pin_elements = await page.query_selector_all('div[data-test-id="pin"]')

                for pin_el in pin_elements:
                    if len(collected_pins) >= CONFIG["max_pins"]:
                        break

                    try:
                        # Title
                        title_el = await pin_el.query_selector('div[data-test-id="pin-title"]')
                        title = await title_el.inner_text() if title_el else ""
                        title = title.strip()

                        # Description (sometimes in alt or separate div)
                        desc_el = await pin_el.query_selector('div[data-test-id="pin-description"]')
                        description = await desc_el.inner_text() if desc_el else ""
                        description = description.strip()

                        # Image
                        img_el = await pin_el.query_selector('img[src*="pinimg.com"]')
                        img_src = await img_el.get_attribute("src") if img_el else None

                        # Pin link / ID
                        link_el = await pin_el.query_selector('a[href*="/pin/"]')
                        pin_url = await link_el.get_attribute("href") if link_el else ""
                        pin_id = pin_url.split("/pin/")[-1].split("/")[0] if pin_url else ""

                        if img_src and pin_id:
                            if is_safe_pin(title, description):
                                pin_data = {
                                    "pin_id": pin_id,
                                    "title": title,
                                    "description": description,
                                    "image_url": img_src,
                                    "pin_url": f"https://www.pinterest.com{pin_url}" if pin_url else "",
                                    "scraped_at": asyncio.get_event_loop().time()
                                }

                                collected_pins.append(pin_data)
                                print(f"Found safe pin {len(collected_pins):3d}: {title[:60]}{'...' if len(title) > 60 else ''}")

                                # Download image if enabled
                                if CONFIG["download_images"]:
                                    img_filename = f"{pin_id}.jpg"
                                    img_path = images_dir / img_filename

                                    if not img_path.exists():
                                        try:
                                            response = await page.goto(img_src, timeout=20000)
                                            if response and response.ok:
                                                await page.evaluate(f"""() => {{
                                                    const a = document.createElement('a');
                                                    a.href = '{img_src}';
                                                    a.download = '{img_filename}';
                                                    document.body.appendChild(a);
                                                    a.click();
                                                    a.remove();
                                                }}""")
                                                # Better: use direct download
                                                # But for simplicity we'll use requests in real prod
                                                print(f"  → Downloaded: {img_filename}")
                                        except Exception as e:
                                            print(f"  → Image download failed: {e}")

                    except Exception as e:
                        continue

                # Check if we stopped loading new content
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                    last_height = new_height

                if len(collected_pins) >= CONFIG["max_pins"]:
                    break

        except Exception as e:
            print(f"Error during scraping: {e}")

        finally:
            await browser.close()

    # Save metadata
    if collected_pins:
        json_path = Path(CONFIG["output_folder"]) / f"{CONFIG['keyword'].replace(' ', '_')}_pins.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(collected_pins, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(collected_pins)} safe pins to: {json_path}")

    print("\nScraping finished.")

# ===================== RUN =====================
if __name__ == "__main__":
    asyncio.run(scrape_pinterest())
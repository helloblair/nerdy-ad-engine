"""
competitor_scraper.py
---------------------
Scrapes publicly available competitor ad data from Meta Ad Library.
Uses Playwright to render the JavaScript-heavy Ad Library pages and
extract ad creative text, metadata, and activity status.

Usage:
    python competitor_scraper.py                    # Scrape all competitors
    python competitor_scraper.py --competitor chegg  # Scrape one competitor
    python competitor_scraper.py --dry-run           # Preview without saving

Output:
    reference_ads/competitors/{competitor_name}.json
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout
except ImportError:
    print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# ─── Competitor Configuration ────────────────────────────────────────────────

COMPETITORS = {
    "khan_academy": {
        "page_id": "22580224300",
        "display_name": "Khan Academy",
        "search_terms": ["Khan Academy"],
    },
    "chegg": {
        "page_id": "34505931453",
        "display_name": "Chegg",
        "search_terms": ["Chegg"],
    },
    "course_hero": {
        "page_id": "206560366033373",
        "display_name": "Course Hero",
        "search_terms": ["Course Hero"],
    },
    "wyzant": {
        "page_id": "112040885475808",
        "display_name": "Wyzant",
        "search_terms": ["Wyzant"],
    },
    "princeton_review": {
        "page_id": "7580188544",
        "display_name": "The Princeton Review",
        "search_terms": ["Princeton Review"],
    },
    "kaplan": {
        "page_id": "10708370283",
        "display_name": "Kaplan",
        "search_terms": ["Kaplan test prep", "Kaplan tutoring"],
    },
    "sylvan": {
        "page_id": "22174638102",
        "display_name": "Sylvan Learning",
        "search_terms": ["Sylvan Learning"],
    },
    "kumon": {
        "page_id": "112491738797367",
        "display_name": "Kumon",
        "search_terms": ["Kumon"],
    },
}

# Meta Ad Library base URL (publicly accessible, no login required)
AD_LIBRARY_URL = "https://www.facebook.com/ads/library/"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "reference_ads" / "competitors"


# ─── Scraper ──────────────────────────────────────────────────────────────────

class MetaAdLibraryScraper:
    """Scrapes ad data from Meta's publicly accessible Ad Library."""

    def __init__(self, headless: bool = True, max_ads_per_competitor: int = 20):
        self.headless = headless
        self.max_ads = max_ads_per_competitor
        self.browser = None
        self.context = None

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        return self

    async def __aexit__(self, *args):
        if self.browser:
            await self.browser.close()
        await self._pw.stop()

    def _build_search_url(self, page_id: str) -> str:
        """Build the Ad Library search URL for a specific page ID."""
        return (
            f"{AD_LIBRARY_URL}"
            f"?active_status=active"
            f"&ad_type=all"
            f"&country=US"
            f"&view_all_page_id={page_id}"
            f"&search_type=page"
            f"&media_type=all"
        )

    async def _dismiss_cookie_banner(self, page: Page):
        """Click through Meta's cookie consent if it appears."""
        try:
            cookie_btn = page.locator(
                'button[data-cookiebanner="accept_only_essential_button"], '
                'button[data-cookiebanner="accept_button"], '
                'button:has-text("Allow all cookies"), '
                'button:has-text("Allow essential and optional cookies"), '
                'button:has-text("Decline optional cookies")'
            )
            await cookie_btn.first.click(timeout=5000)
            await page.wait_for_timeout(1000)
        except (PlaywrightTimeout, Exception):
            pass  # No cookie banner or already dismissed

    async def _scroll_to_load(self, page: Page, max_scrolls: int = 8):
        """Scroll down to trigger lazy-loading of more ad cards."""
        for _ in range(max_scrolls):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

    async def _extract_ads_from_page(self, page: Page, competitor_key: str) -> list[dict]:
        """Extract ad data from the rendered Ad Library page."""
        ads = []

        # Meta Ad Library renders ad cards in divs with specific structure.
        # The selectors target the publicly visible ad card layout.
        # These may need updating if Meta changes their markup.
        ad_cards = page.locator(
            'div[class*="xrvj5dj"], '       # Common ad card container class
            'div[class*="_7jvw"], '           # Legacy ad card class
            'div[role="article"], '           # Semantic article containers
            'div[class*="x1dr59a3"]'          # 2024+ ad card wrapper
        )

        count = await ad_cards.count()
        if count == 0:
            # Fallback: try to find ad content blocks by structure
            ad_cards = page.locator('div:has(> div > span:has-text("Active"))')
            count = await ad_cards.count()

        print(f"  Found {count} ad card elements for {competitor_key}")

        for i in range(min(count, self.max_ads)):
            try:
                card = ad_cards.nth(i)
                ad_data = await self._parse_ad_card(card, competitor_key, i)
                if ad_data and ad_data.get("primary_text") and ad_data.get("is_active"):
                    ads.append(ad_data)
            except Exception as e:
                print(f"  ⚠ Failed to parse ad card {i}: {e}")
                continue

        # Sort by longevity — longest-running ads first (best performance proxy)
        ads.sort(key=lambda a: a.get("days_active") or 0, reverse=True)
        return ads

    async def _parse_ad_card(self, card, competitor_key: str, index: int) -> Optional[dict]:
        """Parse a single ad card element into structured data."""
        try:
            # Get all text content from the card
            all_text = await card.inner_text()
            lines = [l.strip() for l in all_text.split("\n") if l.strip()]

            if len(lines) < 2:
                return None

            # Extract primary text (usually the longest text block)
            text_blocks = [l for l in lines if len(l) > 20]
            primary_text = text_blocks[0] if text_blocks else lines[0]

            # Look for headline (often shorter, appears after primary text)
            headline = ""
            for line in lines:
                if line != primary_text and 5 < len(line) < 100:
                    headline = line
                    break

            # Look for CTA button text
            cta = ""
            cta_patterns = [
                "Learn More", "Sign Up", "Book Now", "Get Started",
                "Shop Now", "Download", "Subscribe", "Apply Now",
                "Contact Us", "Get Offer", "Book a Free Session",
                "Start Free Trial", "Try Free", "See More",
            ]
            for line in lines:
                for pattern in cta_patterns:
                    if pattern.lower() in line.lower():
                        cta = pattern
                        break
                if cta:
                    break

            # Check if ad is marked as active
            is_active = any("active" in l.lower() for l in lines[:5])

            # Try to extract start date
            start_date = None
            date_pattern = re.compile(r'Started running on\s+(.+?)(?:\s*$|\s*·)', re.IGNORECASE)
            for line in lines:
                match = date_pattern.search(line)
                if match:
                    start_date = match.group(1).strip()
                    break

            # Detect platform mentions
            platforms = []
            platform_text = " ".join(lines[:10]).lower()
            if "facebook" in platform_text:
                platforms.append("facebook")
            if "instagram" in platform_text:
                platforms.append("instagram")
            if "messenger" in platform_text:
                platforms.append("messenger")
            if "audience network" in platform_text:
                platforms.append("audience_network")
            if not platforms:
                platforms = ["facebook"]  # Default assumption

            # Compute days_active from start_date
            days_active = None
            if start_date:
                try:
                    from dateutil import parser as dateutil_parser
                    parsed = dateutil_parser.parse(start_date)
                    days_active = (datetime.now(timezone.utc) - parsed.replace(tzinfo=timezone.utc)).days
                except Exception:
                    days_active = None

            return {
                "id": f"{competitor_key}_{index + 1:03d}",
                "competitor": competitor_key,
                "primary_text": primary_text,
                "headline": headline,
                "cta_button": cta or "Learn More",
                "platforms": platforms,
                "is_active": is_active,
                "start_date": start_date,
                "days_active": days_active,
                "scraped_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }

        except Exception:
            return None

    async def scrape_competitor(self, competitor_key: str) -> list[dict]:
        """Scrape all active ads for a single competitor."""
        config = COMPETITORS.get(competitor_key)
        if not config:
            print(f"❌ Unknown competitor: {competitor_key}")
            return []

        print(f"\n🔍 Scraping {config['display_name']} (page_id: {config['page_id']})...")

        page = await self.context.new_page()
        ads = []

        try:
            url = self._build_search_url(config["page_id"])
            print(f"  URL: {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._dismiss_cookie_banner(page)

            # Wait for ad content to render
            try:
                await page.wait_for_selector(
                    'div[role="article"], div[class*="_7jvw"], div[class*="xrvj5dj"]',
                    timeout=15000,
                )
            except PlaywrightTimeout:
                print(f"  ⚠ No ad cards loaded for {config['display_name']} — page may require different selectors")
                # Take a screenshot for debugging
                debug_dir = Path(__file__).parent / "data" / "debug"
                debug_dir.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(debug_dir / f"{competitor_key}_debug.png"))
                print(f"  📸 Debug screenshot saved to data/debug/{competitor_key}_debug.png")
                return []

            # Scroll to load more ads
            await self._scroll_to_load(page)

            # Extract ads
            ads = await self._extract_ads_from_page(page, competitor_key)
            print(f"  ✅ Extracted {len(ads)} ads for {config['display_name']}")

        except Exception as e:
            print(f"  ❌ Error scraping {config['display_name']}: {e}")
        finally:
            await page.close()

        return ads

    async def scrape_all(self, competitor_keys: Optional[list[str]] = None) -> dict[str, list[dict]]:
        """Scrape ads for all (or specified) competitors."""
        keys = competitor_keys or list(COMPETITORS.keys())
        results = {}

        for key in keys:
            ads = await self.scrape_competitor(key)
            results[key] = ads
            # Brief pause between competitors to be respectful
            await asyncio.sleep(2)

        return results


# ─── Output ───────────────────────────────────────────────────────────────────

def save_competitor_ads(competitor_key: str, ads: list[dict]):
    """Save scraped ads to a JSON file matching the varsity_tutors.json schema."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = COMPETITORS[competitor_key]

    output = {
        "source": f"{config['display_name']} — scraped from Meta Ad Library (public data)",
        "competitor": competitor_key,
        "display_name": config["display_name"],
        "page_id": config["page_id"],
        "scraped_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "total_ads_found": len(ads),
        "ads": ads,
    }

    output_path = OUTPUT_DIR / f"{competitor_key}.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  💾 Saved {len(ads)} ads to {output_path}")


def print_summary(results: dict[str, list[dict]]):
    """Print a summary of scraping results."""
    print(f"\n{'='*60}")
    print("SCRAPING SUMMARY")
    print(f"{'='*60}")
    total = 0
    for key, ads in results.items():
        name = COMPETITORS[key]["display_name"]
        print(f"  {name:25s} — {len(ads)} ads")
        total += len(ads)
    print(f"{'─'*60}")
    print(f"  {'TOTAL':25s} — {total} ads")
    print(f"{'='*60}\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Scrape competitor ads from Meta Ad Library")
    parser.add_argument("--competitor", type=str, help="Scrape a single competitor (e.g., 'chegg')")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving to disk")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode (visible)")
    parser.add_argument("--max-ads", type=int, default=20, help="Max ads to collect per competitor")
    parser.add_argument("--list", action="store_true", help="List available competitors and exit")
    args = parser.parse_args()

    if args.list:
        print("\nAvailable competitors:")
        for key, config in COMPETITORS.items():
            print(f"  {key:20s} — {config['display_name']} (page_id: {config['page_id']})")
        return

    keys = [args.competitor] if args.competitor else None

    if args.competitor and args.competitor not in COMPETITORS:
        print(f"❌ Unknown competitor: {args.competitor}")
        print(f"   Available: {', '.join(COMPETITORS.keys())}")
        return

    print("🚀 Meta Ad Library Competitor Scraper")
    print(f"   Mode: {'dry run' if args.dry_run else 'scrape + save'}")
    print(f"   Browser: {'headed' if args.headed else 'headless'}")
    print(f"   Max ads per competitor: {args.max_ads}")
    print(f"   Targets: {', '.join(keys or COMPETITORS.keys())}")

    async with MetaAdLibraryScraper(
        headless=not args.headed,
        max_ads_per_competitor=args.max_ads,
    ) as scraper:
        results = await scraper.scrape_all(keys)

    print_summary(results)

    if not args.dry_run:
        for key, ads in results.items():
            if ads:
                save_competitor_ads(key, ads)
        print("✅ All competitor data saved to reference_ads/competitors/")
    else:
        print("🔍 Dry run complete — no files written")
        # Print a sample of what was found
        for key, ads in results.items():
            if ads:
                print(f"\n  Sample from {key}:")
                sample = ads[0]
                print(f"    Primary text: {sample['primary_text'][:100]}...")
                print(f"    Headline:     {sample.get('headline', 'N/A')[:60]}")
                print(f"    CTA:          {sample.get('cta_button', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())

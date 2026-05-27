"""
999.md iPhone listings scraper using Playwright.
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from utils.helpers import extract_iphone_model, parse_price, random_delay


@dataclass
class ScrapedListing:
    """Data class for scraped listing."""
    external_id: str
    title: str
    description: str
    model: str
    storage_gb: Optional[int]
    color: Optional[str]
    battery_health: Optional[int]
    condition: Optional[str]
    price: float
    currency: str
    listing_url: str
    images: List[str]
    location: Optional[str]
    posted_at: Optional[datetime]
    seller_name: Optional[str]
    seller_external_id: Optional[str]


class NinesScraper:
    """Scraper for 999.md iPhone listings."""
    
    BASE_URL = "https://999.md"
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        ]
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.init_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def init_browser(self):
        """Initialize Playwright browser with stealth settings."""
        playwright = await async_playwright().start()
        
        # Browser launch options
        browser_options = {
            "headless": True,
        }
        
        if settings.use_proxies and settings.proxies:
            browser_options["proxy"] = {"server": settings.proxies[0]}
        
        self.browser = await playwright.chromium.launch(**browser_options)
        
        # Context options for fingerprint randomization
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": self._get_random_user_agent(),
            "locale": "ro-RO",
            "timezone_id": "Europe/Chisinau",
            "geolocation": {"latitude": 47.0105, "longitude": 28.8638},
            "permissions": ["geolocation"],
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Add stealth scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
        """)
        
        self.page = await self.context.new_page()
        
        logger.info("Browser initialized with stealth settings")
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent."""
        import random
        return random.choice(self.user_agents)
    
    async def close(self):
        """Close browser and context."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Browser closed")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_page(self, url: str) -> str:
        """Fetch page content with retries."""
        try:
            await random_delay(settings.random_delay_min, settings.random_delay_max)
            
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")

            # Dismiss first-visit onboarding / consent popups that can block
            # scrolling and lazy rendering of listings.
            await self._dismiss_interfering_popups()
            
            # Wait for listings to load.
            #
            # 999.md sometimes loads content a bit slower / differently depending on
            # anti-bot measures. If the selector doesn't appear in time, we still
            # attempt to parse the HTML we got to avoid aborting the whole scrape.
            try:
                await self.page.wait_for_selector(".ads-list-photo-item", timeout=6000)
            except Exception as e:
                logger.warning(f"Listings selector not found in time for {url}: {e}")
                # Try scrolling to trigger client-side rendering / lazy loading.
                try:
                    for _ in range(2):
                        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await self.page.wait_for_timeout(800)
                    await self._dismiss_interfering_popups()
                    await self.page.wait_for_selector(".ads-list-photo-item", timeout=2000)
                except Exception:
                    pass
            
            content = await self.page.content()
            return content
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise

    async def _dismiss_interfering_popups(self):
        """Close known modal popups that block interaction on 999.md."""
        popup_buttons = [
            "Am înțeles",
            "Am inteles",
            "Închide",
            "Inchide",
        ]
        for label in popup_buttons:
            try:
                btn = self.page.get_by_role("button", name=label)
                if await btn.count():
                    await btn.first.click(timeout=1500)
                    await self.page.wait_for_timeout(500)
            except Exception:
                continue
    
    async def scrape_listings(self, max_pages: int = None) -> List[ScrapedListing]:
        """Scrape all iPhone listings."""
        max_pages = max_pages or settings.max_pages_per_run
        listings = []
        
        for page_num in range(1, max_pages + 1):
            try:
                url = self._build_page_url(page_num)
                logger.info(f"Scraping page {page_num}: {url}")
                
                content = await self.fetch_page(url)
                page_listings = self._parse_listings_page(content)
                
                if not page_listings:
                    logger.info(f"No listings found on page {page_num}, stopping")
                    break
                
                listings.extend(page_listings)
                logger.info(f"Found {len(page_listings)} listings on page {page_num}")
                
            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {e}")
                continue
        
        logger.info(f"Total listings scraped: {len(listings)}")
        return listings
    
    def _build_page_url(self, page: int) -> str:
        """Build paginated URL."""
        base_url = settings.target_url
        if page > 1:
            return f"{base_url}&page={page}"
        return base_url
    
    def _parse_listings_page(self, html: str) -> List[ScrapedListing]:
        """Parse listings from page HTML."""
        soup = BeautifulSoup(html, "lxml")
        listings = []
        
        # Find all listing items
        items = soup.find_all("li", class_="ads-list-photo-item")
        
        for item in items:
            try:
                listing = self._parse_listing_item(item)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.warning(f"Error parsing listing item: {e}")
                continue

        # Fallback for updated website markup where legacy classes are missing.
        if not listings:
            listings = self._parse_listings_fallback(soup)
        
        return listings

    def _parse_listings_fallback(self, soup: BeautifulSoup) -> List[ScrapedListing]:
        """Fallback parser based on generic anchors/text when classes change."""
        listings: List[ScrapedListing] = []
        seen_ids = set()

        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if "/ro/" not in href:
                continue

            link_text = link.get_text(" ", strip=True)
            context_text = link.parent.get_text(" ", strip=True) if link.parent else link_text
            combined_text = f"{link_text} {context_text}".strip()
            if "iphone" not in combined_text.lower():
                continue

            external_id = self._extract_listing_id(href)
            if not external_id or external_id in seen_ids:
                continue
            seen_ids.add(external_id)

            title = link_text or combined_text[:180]
            if not title:
                continue

            # Extract price from the context text surrounding the link, not the
            # title itself, to avoid picking up model numbers (e.g. "15" from
            # "iPhone 15 Pro") as prices.
            price_candidates = re.findall(
                r"(\d[\d\s.,]*)\s*(?:lei|mdl|€|eur|\$|usd)",
                combined_text,
                re.IGNORECASE,
            )
            price = 0.0
            currency = "MDL"
            for candidate in price_candidates:
                p, c = parse_price(candidate + " lei")
                if p >= 500:
                    price = p
                    currency = c
                    break
            if price <= 0:
                price, currency = parse_price(combined_text)
            if price <= 0 or price < 500:
                continue

            model, storage_gb, color = extract_iphone_model(title)
            listing_url = urljoin(self.BASE_URL, href)

            listings.append(
                ScrapedListing(
                    external_id=external_id,
                    title=title,
                    description="",
                    model=model or "Unknown",
                    storage_gb=storage_gb,
                    color=color,
                    battery_health=None,
                    condition=None,
                    price=price,
                    currency=currency,
                    listing_url=listing_url,
                    images=[],
                    location=None,
                    posted_at=None,
                    seller_name=None,
                    seller_external_id=None,
                )
            )

            # Keep fallback bounded and fast.
            if len(listings) >= 300:
                break

        if listings:
            logger.info(f"Fallback parser extracted {len(listings)} listings")
        return listings
    
    def _parse_listing_item(self, item) -> Optional[ScrapedListing]:
        """Parse individual listing item."""
        try:
            # Extract link and ID
            link_elem = item.find("a", class_="js-item-ad")
            if not link_elem:
                return None
            
            href = link_elem.get("href", "")
            external_id = self._extract_listing_id(href)
            listing_url = urljoin(self.BASE_URL, href)
            
            # Extract title
            title_elem = item.find("div", class_="ads-list-photo-item-title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extract price
            price_elem = item.find("span", class_="ads-list-photo-item-price")
            price_text = price_elem.get_text(strip=True) if price_elem else "0"
            price, currency = parse_price(price_text)
            
            # Extract image
            img_elem = item.find("img")
            images = []
            if img_elem:
                img_url = img_elem.get("src") or img_elem.get("data-src")
                if img_url:
                    images.append(urljoin(self.BASE_URL, img_url))
            
            # Extract location
            location_elem = item.find("span", class_="ads-list-photo-item-location")
            location = location_elem.get_text(strip=True) if location_elem else None
            
            # Extract posting time
            time_elem = item.find("span", class_="js-ads-list-photo-item-date")
            posted_at = self._parse_posting_time(time_elem.get_text(strip=True) if time_elem else None)
            
            # Parse iPhone details from title
            model, storage_gb, color = extract_iphone_model(title)
            
            return ScrapedListing(
                external_id=external_id,
                title=title,
                description="",  # Will be filled from detail page
                model=model or "Unknown",
                storage_gb=storage_gb,
                color=color,
                battery_health=None,  # Will be filled from detail page
                condition=None,  # Will be filled from detail page
                price=price,
                currency=currency,
                listing_url=listing_url,
                images=images,
                location=location,
                posted_at=posted_at,
                seller_name=None,  # Will be filled from detail page
                seller_external_id=None,  # Will be filled from detail page
            )
            
        except Exception as e:
            logger.warning(f"Error parsing item: {e}")
            return None
    
    def _extract_listing_id(self, href: str) -> str:
        """Extract listing ID from URL."""
        match = re.search(r"/item/(\d+)", href)
        if match:
            return match.group(1)
        return href.strip("/").split("/")[-1]
    
    def _parse_posting_time(self, time_text: Optional[str]) -> Optional[datetime]:
        """Parse posting time from text."""
        if not time_text:
            return None
        
        # Handle relative times
        now = datetime.now()
        
        if "astazi" in time_text.lower() or "azi" in time_text.lower():
            return now
        
        if "ieri" in time_text.lower():
            return now.replace(day=now.day - 1)
        
        # Try to parse specific patterns
        patterns = [
            r"(\d+)\s+minute",
            r"(\d+)\s+ore",
            r"(\d+)\s+zile",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, time_text.lower())
            if match:
                value = int(match.group(1))
                if "minut" in pattern:
                    return now.replace(minute=max(0, now.minute - value))
                elif "or" in pattern:
                    return now.replace(hour=max(0, now.hour - value))
                elif "zil" in pattern:
                    return now.replace(day=max(1, now.day - value))
        
        return now
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def scrape_listing_details(self, listing_url: str) -> dict:
        """Scrape detailed information from listing page."""
        try:
            # Keep detail scraping lightweight so parser cycles stay fast.
            await random_delay(0, 1)
            
            response = await self.page.goto(listing_url, wait_until="networkidle", timeout=30000)
            
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "lxml")
            
            details = {
                "description": "",
                "battery_health": None,
                "condition": None,
                "seller_name": None,
                "seller_phone": None,
                "all_images": [],
                "features": [],
            }
            
            # Extract description
            desc_elem = soup.find("div", class_="adPage__content__description")
            if desc_elem:
                details["description"] = desc_elem.get_text(separator="\n", strip=True)
            
            # Extract all images
            img_elems = soup.find_all("img", class_="adPage__content__photos__thumbnail")
            for img in img_elems:
                img_url = img.get("src") or img.get("data-src")
                if img_url:
                    details["all_images"].append(urljoin(self.BASE_URL, img_url))
            
            # Extract seller info
            seller_elem = soup.find("div", class_="adPage__aside__author")
            if seller_elem:
                name_elem = seller_elem.find("a", class_="adPage__aside__author__name")
                if name_elem:
                    details["seller_name"] = name_elem.get_text(strip=True)
                
                phone_elem = seller_elem.find("a", class_="adPage__aside__phone")
                if phone_elem:
                    details["seller_phone"] = phone_elem.get("href", "").replace("tel:", "")
            
            # Parse features and characteristics
            chars = soup.find_all("li", class_="adPage__content__features__item")
            for char in chars:
                label = char.find("span", class_="adPage__content__features__key")
                value = char.find("span", class_="adPage__content__features__value")
                
                if label and value:
                    label_text = label.get_text(strip=True).lower()
                    value_text = value.get_text(strip=True)
                    details["features"].append({label_text: value_text})
                    
                    # Extract battery health
                    if "starea bateriei" in label_text or "battery" in label_text:
                        battery_match = re.search(r"(\d+)", value_text)
                        if battery_match:
                            details["battery_health"] = int(battery_match.group(1))
                    
                    # Extract condition
                    if "stare" in label_text or "condition" in label_text:
                        details["condition"] = value_text
            
            return details
            
        except Exception as e:
            logger.error(f"Error scraping details for {listing_url}: {e}")
            return {}

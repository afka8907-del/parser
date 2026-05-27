---
name: testing-parser-bot
description: Test the 999.md iPhone scraper and Telegram bot end-to-end. Use when verifying scraper, bot, or price parsing changes.
---

# Testing the iPhone Parser Bot

## Project Structure

- `main.py` — Entry point. Modes: `bot`, `scheduler`, `api`, `all`
- `parser/scraper.py` — 999.md scraper using Playwright + BeautifulSoup
- `bot/telegram_bot.py` — Telegram bot (aiogram 3.x) with inline keyboard menus
- `analyzer/deal_detector.py` — Deal detection and profit scoring
- `analyzer/market_analyzer.py` — Market statistics and model demand scores
- `utils/helpers.py` — Price parsing, model extraction, profit calculation
- `config/settings.py` — Pydantic settings (reads from `.env`)
- `database/` — SQLAlchemy async models (SQLite at `data/iphone_market.db`)

## Devin Secrets Needed

- `TELEGRAM_BOT_TOKEN` — Required to run the bot. Stored in `.env` file.

## Running the Bot

```bash
cd <repo_root>
python main.py bot
```

**Important:** Must run from the project directory — pydantic-settings looks for `.env` relative to CWD.

**Common issue:** `TelegramConflictError` means another bot instance is running. Kill it first:
```bash
pkill -f "main.py bot"
```

## Testing the Scraper

The scraper targets 999.md which uses React with CSS-module hashed classes. The class names contain stable substrings like `advert__photo__link`, `advert__photo__title`, `price__text`.

To test scraper parsing without hitting the live site:

1. Save a page from 999.md using Playwright:
```python
import asyncio
from playwright.async_api import async_playwright

async def save_page():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()
    url = 'https://999.md/ro/list/phone-and-communication/mobile-phones?o_16_1=776&applied=1'
    await page.goto(url, wait_until='networkidle', timeout=30000)
    content = await page.content()
    with open('saved_page.html', 'w', encoding='utf-8') as f:
        f.write(content)
    await browser.close()
    await pw.stop()

asyncio.run(save_page())
```

2. Test parsing against the saved HTML:
```python
from parser.scraper import NinesScraper
scraper = NinesScraper()
with open('saved_page.html', 'r', encoding='utf-8') as f:
    html = f.read()
listings = scraper._parse_listings_page(html)
print(f'{len(listings)} listings, {sum(1 for l in listings if l.price < 500)} bad prices')
```

**Key assertions:**
- At least 100 listings parsed from a full page
- Zero listings with price < 500 MDL (rejects model numbers parsed as prices)
- Listing URLs start with `https://999.md/ro/`
- External IDs are numeric strings of 5+ digits

## Testing the Bot Module

Verify imports and keyboard structure:
```python
from bot.telegram_bot import _main_menu_kb, _models_kb
kb = _main_menu_kb()
assert len(kb.inline_keyboard) == 4  # 4 rows of 2 buttons
```

## Verifying Telegram API State

Check registered commands (replace TOKEN):
```python
import urllib.request, json
resp = urllib.request.urlopen(f'https://api.telegram.org/bot{TOKEN}/getMyCommands')
print(json.loads(resp.read()))
```

Expected: exactly 4 commands (start, search, profit, help).

## Testing Price Parsing

999.md prices use space-separated thousands: `"21 999 MDL"`, `"1 280 €"`.

```python
from utils.helpers import parse_price
assert parse_price('21 999 MDL') == (21999.0, 'MDL')
assert parse_price('15.500 lei') == (15500.0, 'MDL')  # European dot-thousands
```

## Testing Model Detection

```python
from utils.helpers import extract_iphone_model
model, storage, color = extract_iphone_model('iPhone 16 Pro Max 256GB')
assert model == 'iPhone 16 Pro Max' and storage == 256
```

**Known limitation:** `1TB` storage is not parsed (regex only matches `\d+\s*GB`).

## Common Gotchas

- 999.md might change their CSS-module class hashes. If scraper returns 0 listings, save a fresh page and inspect with `grep -oi 'class="[^"]*advert[^"]*"'` to find new class patterns.
- The bot's inline keyboards use callback_data strings like `menu_topdeals`, `model_iPhone 16 Pro`. The callback router in `on_callback()` handles all navigation.
- The database might have old listings with bad prices from before the scraper fix. Run `python main.py scheduler` to re-scrape and update.
- Dependencies may have version conflicts. Install core deps individually if `pip install -r requirements.txt` fails.

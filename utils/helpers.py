"""
Utility helper functions.
"""

import asyncio
import random
import re
from typing import Optional, Tuple

import fake_useragent


def get_random_user_agent() -> str:
    """Get a random realistic user agent."""
    try:
        ua = fake_useragent.UserAgent()
        return ua.random
    except:
        # Fallback user agents
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        ]
        return random.choice(agents)


async def random_delay(min_seconds: int = 2, max_seconds: int = 5):
    """Random delay to avoid detection."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


def parse_price(price_text: str) -> Tuple[float, str]:
    """
    Parse price from text.
    
    Returns:
        Tuple of (price_value, currency)
    """
    if not price_text:
        return 0.0, "MDL"
    
    # Remove spaces and normalize
    text = price_text.replace(" ", "").replace("\u00a0", "").lower()
    
    # Extract currency
    currency = "MDL"
    if "€" in text or "eur" in text or "euro" in text:
        currency = "EUR"
    elif "$" in text or "usd" in text:
        currency = "USD"
    elif "lei" in text:
        currency = "MDL"
    
    # Extract number
    # Handle formats like "15,500", "15500", "15.500"
    number_match = re.search(r"[\d.,]+", text)
    if number_match:
        number_str = number_match.group()
        # Normalize decimal/thousands separator
        if "," in number_str and "." in number_str:
            # Format like 1,500.50
            number_str = number_str.replace(",", "")
        elif "," in number_str:
            # Could be thousands separator or decimal
            parts = number_str.split(",")
            if len(parts[-1]) == 2:
                # Likely decimal
                number_str = number_str.replace(",", ".")
            else:
                # Likely thousands
                number_str = number_str.replace(",", "")
        elif "." in number_str:
            # Could be thousands separator (European style) or decimal
            parts = number_str.split(".")
            if len(parts) == 2 and len(parts[-1]) == 3:
                # e.g. "15.500" -> 15500 (thousands separator)
                number_str = number_str.replace(".", "")
        
        try:
            price = float(number_str)
            return price, currency
        except ValueError:
            pass
    
    return 0.0, currency


def extract_iphone_model(text: str) -> Tuple[str, Optional[int], Optional[str]]:
    """
    Extract iPhone model, storage, and color from text.
    
    Returns:
        Tuple of (model_name, storage_gb, color)
    """
    text_lower = text.lower()
    
    # iPhone models to detect
    models = [
        ("iPhone 15 Pro Max", ["iphone 15 pro max", "15 pro max", "15promax"]),
        ("iPhone 15 Pro", ["iphone 15 pro", "15 pro", "15pro"]),
        ("iPhone 15 Plus", ["iphone 15 plus", "15 plus", "15plus"]),
        ("iPhone 15", ["iphone 15", "15 "]),
        ("iPhone 14 Pro Max", ["iphone 14 pro max", "14 pro max", "14promax"]),
        ("iPhone 14 Pro", ["iphone 14 pro", "14 pro", "14pro"]),
        ("iPhone 14 Plus", ["iphone 14 plus", "14 plus", "14plus"]),
        ("iPhone 14", ["iphone 14", "14 "]),
        ("iPhone 13 Pro Max", ["iphone 13 pro max", "13 pro max", "13promax"]),
        ("iPhone 13 Pro", ["iphone 13 pro", "13 pro", "13pro"]),
        ("iPhone 13 mini", ["iphone 13 mini", "13 mini", "13mini"]),
        ("iPhone 13", ["iphone 13", "13 "]),
        ("iPhone 12 Pro Max", ["iphone 12 pro max", "12 pro max", "12promax"]),
        ("iPhone 12 Pro", ["iphone 12 pro", "12 pro", "12pro"]),
        ("iPhone 12 mini", ["iphone 12 mini", "12 mini", "12mini"]),
        ("iPhone 12", ["iphone 12", "12 "]),
        ("iPhone 11 Pro Max", ["iphone 11 pro max", "11 pro max", "11promax"]),
        ("iPhone 11 Pro", ["iphone 11 pro", "11 pro", "11pro"]),
        ("iPhone 11", ["iphone 11", "11 "]),
        ("iPhone SE", ["iphone se", "se ", "se2", "se3"]),
        ("iPhone XR", ["iphone xr", " xr"]),
        ("iPhone XS Max", ["iphone xs max", "xs max", "xsmax"]),
        ("iPhone XS", ["iphone xs", " xs"]),
        ("iPhone X", ["iphone x", " x "]),
    ]
    
    detected_model = "Unknown"
    for model_name, patterns in models:
        for pattern in patterns:
            if pattern in text_lower:
                detected_model = model_name
                break
        if detected_model != "Unknown":
            break
    
    # Extract storage
    storage = None
    storage_patterns = [
        r"(\d+)\s*gb",
        r"(\d+)\s*g\b",
        r"(\d+)(?:gb|giga)",
    ]
    
    for pattern in storage_patterns:
        match = re.search(pattern, text_lower)
        if match:
            value = int(match.group(1))
            # Validate common iPhone storage sizes
            if value in [8, 16, 32, 64, 128, 256, 512, 1024]:
                storage = value
                break
    
    # Extract color
    colors = {
        "black": ["black", "negru", "midnight", "space gray", "space grey", "spacegray"],
        "white": ["white", "alb", "silver", "starlight"],
        "red": ["red", "rosu", "product red", "productred"],
        "blue": ["blue", "albastru", "sierra blue", "pacific blue", "deep purple"],
        "green": ["green", "verde", "alpine green", "midnight green"],
        "gold": ["gold", "auriu", "yellow"],
        "purple": ["purple", "mov", "violet"],
        "pink": ["pink", "roz"],
        "gray": ["gray", "grey", "gri", "space gray", "graphite", "titanium"],
    }
    
    detected_color = None
    for color_name, patterns in colors.items():
        for pattern in patterns:
            if pattern in text_lower:
                detected_color = color_name
                break
        if detected_color:
            break
    
    return detected_model, storage, detected_color


def calculate_profit_margin(buy_price: float, sell_price: float, costs: float = 0) -> dict:
    """
    Calculate profit metrics.
    
    Returns:
        Dict with profit, margin, and ROI
    """
    gross_profit = sell_price - buy_price
    net_profit = gross_profit - costs
    
    margin_percent = (gross_profit / buy_price * 100) if buy_price > 0 else 0
    roi_percent = (net_profit / (buy_price + costs) * 100) if (buy_price + costs) > 0 else 0
    
    return {
        "buy_price": buy_price,
        "sell_price": sell_price,
        "costs": costs,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "margin_percent": round(margin_percent, 2),
        "roi_percent": round(roi_percent, 2),
    }


def format_currency(amount: float, currency: str = "MDL") -> str:
    """Format amount with currency."""
    symbols = {
        "MDL": "MDL",
        "EUR": "€",
        "USD": "$",
    }
    symbol = symbols.get(currency, currency)
    return f"{amount:,.0f} {symbol}"

"""Free Public Phone & Wearables Specs API integration (No API key required).

Fetches live real-time release details, newly announced smartphones, and wearables
via the open-data Phone Specs API (GSMArena community proxy).
"""

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

BASE_URL = "https://phone-specs-api.vercel.app"

BRAND_SLUGS: dict[str, str] = {
    "apple": "apple-phones-48",
    "google": "google-phones-107",
    "samsung": "samsung-phones-9",
    "oneplus": "oneplus-phones-95",
    "xiaomi": "xiaomi-phones-80",
    "vivo": "vivo-phones-98",
    "motorola": "motorola-phones-4",
    "oppo": "oppo-phones-82",
    "realme": "realme-phones-118",
    "sony": "sony-phones-7",
    "asus": "asus-phones-46",
    "nothing": "nothing-phones-128",
}


def fetch_recent_devices(brand: str = "", device_slug: str = "") -> dict[str, Any]:
    """Fetches real-time, live specs and announcements for the latest smartphones and wearables.

    Calls the free public Phone Specs API (no API key required).
    Use this when the user asks about the latest/newest mobile phones, flagship releases,
    smart wearables (e.g., Apple Watch, Galaxy Watch, Pixel Watch/Fold), or needs up-to-date specs.

    Args:
        brand: Optional brand name to fetch latest releases for (e.g., 'Google', 'Apple', 'Samsung', 'Xiaomi', 'OnePlus').
               If omitted or empty, returns the newest announced devices across the entire industry.
        device_slug: Optional specific device slug (e.g., 'google_pixel_11_pro_5g-14801', 'apple_watch_ultra_4-14935')
                     to fetch detailed hardware specifications (display, cameras, battery, chipset, release date).

    Returns:
        A dictionary containing live device lists, hardware specs, release dates, and images.
    """
    try:
        clean_slug = device_slug.strip().lower()
        clean_brand = brand.strip().lower()

        if clean_slug:
            url = f"{BASE_URL}/{clean_slug}"
        elif clean_brand and clean_brand in BRAND_SLUGS:
            brand_slug = BRAND_SLUGS[clean_brand]
            url = f"{BASE_URL}/brands/{brand_slug}"
        else:
            url = f"{BASE_URL}/latest"

        logger.info("Calling public phone specs API: %s", url)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "PhonePilot/1.0 (Smartphone Advisor)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not payload.get("status"):
            return {
                "error": "Device API returned non-success status",
                "details": payload,
            }

        data = payload.get("data", {})

        # If a single device was queried, structure the detailed hardware specifications
        if clean_slug:
            specs_summary: dict[str, dict[str, str]] = {}
            for group in data.get("specifications", []):
                title = group.get("title", "General")
                specs_summary[title] = {
                    s.get("key"): ", ".join(s.get("val", []))
                    for s in group.get("specs", [])
                }
            return {
                "source": "GSMArena Live Open Data",
                "phone_name": data.get("phone_name"),
                "brand": data.get("brand"),
                "release_date": data.get("release_date"),
                "dimension": data.get("dimension"),
                "os": data.get("os"),
                "storage": data.get("storage"),
                "thumbnail": data.get("thumbnail"),
                "specifications": specs_summary,
            }

        # If a list was returned, return top 10 newest items
        phones = data.get("phones", [])[:10]
        return {
            "source": "GSMArena Live Open Data",
            "title": data.get("title", f"Latest {brand.capitalize() or 'Industry'} Devices & Wearables"),
            "devices": [
                {
                    "name": p.get("phone_name"),
                    "slug": p.get("slug"),
                    "image": p.get("image"),
                }
                for p in phones
            ],
        }

    except Exception as exc:
        logger.warning("Failed to fetch from public device API: %s", exc)
        return {
            "error": f"Failed to fetch real-time device data: {exc}",
            "note": "Fallback to internal catalog available.",
        }

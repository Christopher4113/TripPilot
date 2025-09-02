# api/lodging_serpapi.py
import os
import re
import math
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from serpapi import GoogleSearch  # pip install google-search-results

# ---------- Regex helpers ----------
DATE_RANGE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*(?:to|-|–)\s*(\d{4}-\d{2}-\d{2})", re.I)
CITY_CODE_RE  = re.compile(r"\b([A-Z]{3})\b")
GUESTS_RE     = re.compile(r"(\d+)\s*(?:guests?|adults?|pax)", re.I)
BUDGET_NEAR_TOTAL_RE = re.compile(r"([€$£]?\s*\d[\d,]*(?:\.\d{1,2})?)\s*total", re.I)
ANY_MONEY_RE  = re.compile(r"([€$£]?\s*\d[\d,]*(?:\.\d{1,2})?)", re.I)
CUR_SYM_RE    = re.compile(r"[€$£]|\b(?:USD|CAD|EUR|GBP)\b", re.I)

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Minimal IATA->city mapping; extend as needed
IATA_TO_CITY = {
    "MAD": "Madrid, Spain", "LHR": "London, UK", "CDG": "Paris, France",
    "ATH": "Athens, Greece", "FCO": "Rome, Italy", "BER": "Berlin, Germany",
    "AMS": "Amsterdam, Netherlands", "BCN": "Barcelona, Spain", "YYZ": "Toronto, Canada",
    "JFK": "New York, NY", "LAX": "Los Angeles, CA", "SFO": "San Francisco, CA",
}

def _parse_currency(s: str) -> str:
    m = CUR_SYM_RE.search(s or "")
    if not m: return "USD"
    tok = m.group(0).upper()
    return {"$": "USD", "€": "EUR", "£": "GBP"}.get(tok, tok)

def _num(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", "").replace("$", "").replace("€", "").replace("£", "").strip())
    except Exception:
        return None

def _parse_lodging_hint(hint: str) -> Tuple[str, str, str, int, Optional[float], str, int, str]:
    """
    Returns: (city_code, check_in, check_out, adults, total_budget, currency, nights, q_location)
    """
    s = hint or ""

    m_city = CITY_CODE_RE.search(s)
    if not m_city:
        raise ValueError("No IATA city code (e.g., 'MAD') found in lodging hint.")
    city_code = m_city.group(1)
    q_location = IATA_TO_CITY.get(city_code, city_code)  # fallback to code if unknown

    m_dates = DATE_RANGE_RE.search(s)
    if not m_dates:
        raise ValueError("No date range like 'YYYY-MM-DD to YYYY-MM-DD' found in lodging hint.")
    check_in, check_out = m_dates.group(1), m_dates.group(2)
    try:
        dt_in = datetime.fromisoformat(check_in)
        dt_out = datetime.fromisoformat(check_out)
    except Exception:
        raise ValueError("Invalid ISO dates in lodging hint.")
    nights = (dt_out - dt_in).days
    if nights <= 0:
        raise ValueError("Check-out must be after check-in.")

    m_guests = GUESTS_RE.search(s)
    adults = int(m_guests.group(1)) if m_guests else 2

    currency = _parse_currency(s)
    total_budget = None
    near_total = BUDGET_NEAR_TOTAL_RE.search(s)
    if near_total:
        total_budget = _num(near_total.group(1))
    else:
        # last numeric token that's not a date fragment
        candidates = [m.group(1) for m in ANY_MONEY_RE.finditer(s)]
        candidates = [c for c in candidates if "-" not in c]
        if candidates:
            total_budget = _num(candidates[-1])

    return city_code, check_in, check_out, adults, total_budget, currency, nights, q_location

def _estimate_total(property_item: Dict[str, Any], nights: int) -> Optional[float]:
    """
    Heuristics across possible SerpAPI fields:
    - Prefer total_rate.lowest (total for stay)
    - Else rate_per_night * nights
    - Else lowest_price * nights
    - Else prices[0].price * nights (if present as number)
    """
    total_rate = (property_item.get("total_rate") or {})
    if isinstance(total_rate.get("lowest"), (int, float, str)):
        try:
            return float(total_rate["lowest"])
        except Exception:
            pass

    if isinstance(property_item.get("rate_per_night"), (int, float, str)):
        try:
            return float(property_item["rate_per_night"]) * nights
        except Exception:
            pass

    # Some payloads expose 'lowest_price' directly
    if isinstance(property_item.get("lowest_price"), (int, float, str)):
        try:
            return float(property_item["lowest_price"]) * nights
        except Exception:
            pass

    prices = property_item.get("prices") or []
    if prices and isinstance(prices[0], dict):
        # e.g., {"price": 120, "source": "Booking.com", ...}
        p = prices[0].get("price")
        if isinstance(p, (int, float, str)):
            try:
                return float(p) * nights
            except Exception:
                pass

    return None

def _rating_value(property_item: Dict[str, Any]) -> float:
    # 'overall_rating' may be number or string; default 0.0 if missing
    r = property_item.get("overall_rating")
    try:
        return float(r)
    except Exception:
        return 0.0

def _fetch_property_details(property_token: str, params_base: Dict[str, Any]) -> Dict[str, Any]:
    # https://serpapi.com/google-hotels-property-details
    details_params = dict(params_base)
    details_params.update({
        "property_token": property_token,
    })
    details = GoogleSearch(details_params).get_dict()
    return details or {}

def search_best_lodging_from_hint_serpapi(
    hint: str,
    *,
    gl: str = "ca",
    hl: str = "en",
    currency_default: str = "USD",
    nightly_tolerance: float = 1.15,   # allow 15% over nightly budget
    sort_by_lowest_price: bool = True
) -> Dict[str, Any]:
    """
    Parse hint -> Google Hotels via SerpAPI -> choose best within budget.
    Returns { ok, cityCode, checkIn, checkOut, ... , hotel, offer }
    """
    if not SERPAPI_API_KEY:
        return {"ok": False, "error": "SERPAPI_API_KEY missing"}

    try:
        city_code, check_in, check_out, adults, total_budget, currency, nights, q_location = _parse_lodging_hint(hint)
    except Exception as e:
        return {"ok": False, "error": f"parse_error: {e}", "hint": hint}

    currency = currency or currency_default

    # Budget -> nightly bounds for Google Hotels' price filters
    max_price = None
    if total_budget:
        nightly_budget = max(total_budget / max(nights, 1), 1)
        max_price = math.ceil(nightly_budget * nightly_tolerance)

    params = {
        "api_key": SERPAPI_API_KEY,
        "engine": "google_hotels",
        "q": q_location,                     # free-text location (docs: required 'q')
        "check_in_date": check_in,           # YYYY-MM-DD
        "check_out_date": check_out,         # YYYY-MM-DD
        "adults": adults,
        "currency": currency,
        "gl": gl,
        "hl": hl,
        "no_cache": True,                    # always fresh results
    }
    # sort_by options documented; 3 = lowest price
    if sort_by_lowest_price:
        params["sort_by"] = 3               # Lowest price
    if max_price is not None:
        params["max_price"] = max_price

    # Query SerpAPI
    res = GoogleSearch(params).get_dict()   # returns dict with 'properties', 'brands', etc.
    props: List[Dict[str, Any]] = res.get("properties") or []

    # Filter to hotels only (ignore vacation rentals unless you want them)
    hotels = [p for p in props if (p.get("type") or "").lower() == "hotel"]
    if not hotels and props:
        hotels = props  # fall back to whatever is there

    # Rank by: within budget (if any), then lowest total, tie-break by highest rating
    scored: List[Dict[str, Any]] = []
    for p in hotels:
        total_est = _estimate_total(p, nights)
        scored.append({**p, "_total_estimate": total_est})

    def within_budget(p: Dict[str, Any]) -> bool:
        if total_budget is None or p["_total_estimate"] is None:
            return True if total_budget is None else False
        return float(p["_total_estimate"]) <= total_budget * 1.12  # 12% total tolerance

    pool = [p for p in scored if within_budget(p)]
    if not pool:
        pool = scored

    def key_fn(p: Dict[str, Any]):
        total = p["_total_estimate"] if p["_total_estimate"] is not None else float("inf")
        return (total, -_rating_value(p))

    best = sorted(pool, key=key_fn)[0] if pool else None
    if not best:
        return {"ok": False, "error": "no_hotels_found", "meta": {"cityCode": city_code, "q": q_location}}

    # Optional: enrich with Property Details (address, phone, price breakdown)
    details = {}
    token = best.get("property_token")
    if token:
        details = _fetch_property_details(token, {
            "api_key": SERPAPI_API_KEY,
            "engine": "google_hotels",
            "gl": gl, "hl": hl, "currency": currency
        })

    return {
        "ok": True,
        "cityCode": city_code,
        "checkIn": check_in,
        "checkOut": check_out,
        "nights": nights,
        "adults": adults,
        "budgetTotal": total_budget,
        "currency": currency,
        "hotel": {
            "name": best.get("name"),
            "type": best.get("type"),
            "overall_rating": best.get("overall_rating"),
            "check_in_time": best.get("check_in_time"),
            "check_out_time": best.get("check_out_time"),
            "property_token": token,
            "serpapi_property_details_link": best.get("serpapi_property_details_link"),
            "images": best.get("images"),
        },
        "offer": {
            "total_estimate": best.get("_total_estimate"),
            "rate_per_night": best.get("rate_per_night"),
            "price_source": (best.get("prices") or [{}])[0].get("source") if best.get("prices") else None,
        },
        "_counts": {"returned": len(props), "hotels_considered": len(hotels)},
        "_debug": {"applied_max_price": max_price, "q": q_location}
    }

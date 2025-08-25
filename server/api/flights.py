import os
import re
import json
import math
import requests
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

def _get_serpapi_key() -> str:
    # ensure .env is loaded and fetch fresh each call
    load_dotenv()
    key = os.getenv("SERPAPI_API_KEY")
    if not key:
        raise RuntimeError("Missing SERPAPI_API_KEY")
    return key

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"
# Docs: engine=google_flights with fields like departure_id, arrival_id, outbound_date, return_date, adults, travel_class, stops, currency, sort_by, max_price, etc. :contentReference[oaicite:0]{index=0}

# --- Utilities ---------------------------------------------------------------

IATA_RE = re.compile(r"\b([A-Z]{3})\b")
DATE_RANGE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*(?:to|-|–|—)\s*(\d{4}-\d{2}-\d{2})")
PAX_RE = re.compile(r"(\d+)\s*(?:pax|guests?|traveler|travelers)\b", re.I)
CLASS_RE = re.compile(r"\b(economy|premium economy|business|first)\b", re.I)
NONSTOP_RE = re.compile(r"\b(non[-\s]?stop|direct only)\b", re.I)
STOPS_RE = re.compile(r"\b(\d)\s*stop(s)?\b", re.I)
MAX_PRICE_RE = re.compile(r"(?:<=|<=?\s*|\bmax\b|\$)\s*\$?\s*([0-9][0-9,]*)", re.I)
ARROW_SPLIT_RE = re.compile(r"\b([A-Z]{3})\s*(?:->|to|—|–)\s*([A-Z]{3})\b")

TRAVEL_CLASS_MAP = {
    "economy": 1,
    "premium economy": 2,
    "business": 3,
    "first": 4,
}

def _coalesce(*vals):
    for v in vals:
        if v is not None:
            return v
    return None


def parse_flight_hint(hint: str) -> Dict[str, Any]:
    """
    Parse a compact LLM 'hint' like:
      "YYZ->LAX 2025-09-01 to 2025-09-08 2 pax economy nonstop <= $450"
    Returns structured params for SerpAPI.
    """
    hint = hint.strip()

    # 1) origin & destination (prefer explicit IATA arrow pattern)
    od = ARROW_SPLIT_RE.search(hint)
    origin, dest = (od.group(1), od.group(2)) if od else (None, None)

    # fallback: first two IATA codes in the string
    if not (origin and dest):
        codes = IATA_RE.findall(hint)
        if len(codes) >= 2:
            origin, dest = codes[0], codes[1]

    # 2) dates
    dmatch = DATE_RANGE_RE.search(hint)
    outbound_date, return_date = (dmatch.group(1), dmatch.group(2)) if dmatch else (None, None)

    # 3) pax
    pax = 1
    pm = PAX_RE.search(hint)
    if pm:
        pax = max(1, int(pm.group(1)))

    # 4) class
    tclass = 1  # default economy
    cm = CLASS_RE.search(hint)
    if cm:
        tclass = TRAVEL_CLASS_MAP[cm.group(1).lower()]

    # 5) stops
    stops = 0  # 0 = any; 1 = nonstop only; 2 = 1 stop or fewer; 3 = 2 stops or fewer
    if NONSTOP_RE.search(hint):
        stops = 1
    else:
        sm = STOPS_RE.search(hint)
        if sm:
            # interpret "1 stop" -> <=1 stop (code 2); "2 stops" -> <=2 stops (code 3)
            n = int(sm.group(1))
            stops = 1 if n == 0 else min(3, n + 1)

    # 6) budget cap (ticket price)
    max_price = None
    mp = MAX_PRICE_RE.search(hint)
    if mp:
        max_price = int(mp.group(1).replace(",", ""))

    return {
        "origin": origin,
        "dest": dest,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "adults": pax,
        "travel_class": tclass,
        "stops": stops,
        "max_price": max_price,
    }

def _resolve_airport_id_if_needed(text: str) -> Optional[str]:
    """
    Optional helper: if text is already an IATA code (3 letters), return it.
    Otherwise try SerpAPI Airports to resolve the city to a code (best-effort).
    """
    if not text:
        return None
    if IATA_RE.fullmatch(text):
        return text

    api_key = _get_serpapi_key()
    if not api_key:
        return None  # can't resolve without key

    # Airports API: returns "airports" array with objects including airport.id (IATA) for departure/arrival. :contentReference[oaicite:1]{index=1}
    try:
        resp = requests.get(
            SERPAPI_SEARCH_URL,
            params={
                "engine": "google_flights",
                "api_key": api_key,
                "departure_id": text,
                "arrival_id": text,  # trick: ask both; we'll take the first id we see
                "output": "json",
                "json_restrictor": "airports[].{departure[].airport.id,arrival[].airport.id}"
            },
            timeout=30,
        )
        data = resp.json()
        airports = data.get("airports", [])
        for item in airports:
            for side in ("departure", "arrival"):
                arr = item.get(side, [])
                if arr and "airport" in arr[0] and "id" in arr[0]["airport"]:
                    cand = arr[0]["airport"]["id"]
                    if IATA_RE.fullmatch(cand):
                        return cand
    except Exception:
        pass
    return None

# --- SerpAPI call + ranking --------------------------------------------------

def serpapi_flights(params: Dict[str, Any], currency: str = "USD", gl: str = "ca", hl: str = "en") -> Dict[str, Any]:
    """
    Call SerpAPI Google Flights and return JSON.
    """
    api_key = _get_serpapi_key()
    if not api_key:
        raise RuntimeError("Missing SERPAPI_API_KEY")

    q = {
        "engine": "google_flights",
        "api_key": api_key,
        "departure_id": params["origin"],
        "arrival_id": params["dest"],
        "outbound_date": params["outbound_date"],
        "return_date": params["return_date"],
        "adults": params["adults"],
        "travel_class": params["travel_class"],
        "stops": params["stops"],  # 1 = nonstop; 0 = any; etc. :contentReference[oaicite:2]{index=2}
        "type": 1,                 # 1 = round trip :contentReference[oaicite:3]{index=3}
        "currency": currency,
        "gl": gl,   # country
        "hl": hl,   # language
        "sort_by": 1,  # 1 = "Top flights" (SerpAPI mirrors Google) :contentReference[oaicite:4]{index=4}
        "deep_search": "true",  # better parity with UI; slower but more complete :contentReference[oaicite:5]{index=5}
        "output": "json",
    }
    if params.get("max_price"):
        q["max_price"] = params["max_price"]  # price cap if we parsed one :contentReference[oaicite:6]{index=6}

    # Resolve non-IATA inputs if needed
    if not IATA_RE.fullmatch(q["departure_id"]):
        rid = _resolve_airport_id_if_needed(q["departure_id"])
        if rid: q["departure_id"] = rid
    if not IATA_RE.fullmatch(q["arrival_id"]):
        aid = _resolve_airport_id_if_needed(q["arrival_id"])
        if aid: q["arrival_id"] = aid

    resp = requests.get(SERPAPI_SEARCH_URL, params=q, timeout=60)
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"SerpAPI error: {data['error']}")
    return data

def _normalize_flight_item(item: Dict[str, Any], currency: str) -> Dict[str, Any]:
    """Extract a compact summary from a best/other flight item."""
    price = item.get("price")
    total_duration = item.get("total_duration")
    legs = []
    for f in item.get("flights", []):
        legs.append({
            "airline": f.get("airline"),
            "flight_number": f.get("flight_number"),
            "travel_class": f.get("travel_class"),
            "departure": {
                "airport_id": f.get("departure_airport", {}).get("id"),
                "time": f.get("departure_airport", {}).get("time"),
            },
            "arrival": {
                "airport_id": f.get("arrival_airport", {}).get("id"),
                "time": f.get("arrival_airport", {}).get("time"),
            },
            "duration_min": f.get("duration"),
        })
    return {
        "price": price,
        "currency": currency,
        "total_duration_min": total_duration,
        "stops_count": max(0, len(legs) - 1),
        "legs": legs,
        "departure_token": item.get("departure_token"),  # lets you fetch return leg details explicitly :contentReference[oaicite:7]{index=7}
        "booking_token": item.get("booking_token"),      # lets you fetch booking options if needed :contentReference[oaicite:8]{index=8}
    }

def pick_best_flight(data: Dict[str, Any], budget_cap: Optional[int] = None, nonstop_pref: Optional[bool] = None, currency: str = "USD") -> Optional[Dict[str, Any]]:
    """
    Combine best_flights and other_flights; pick by:
      1) within budget (if provided), then lowest price
      2) otherwise globally lowest price
      3) break ties by shortest total_duration
      4) if nonstop_pref, prefer stops_count == 0
    """
    candidates = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    if not candidates:
        return None

    # Normalize
    norm = [_normalize_flight_item(c, currency) for c in candidates]

    def score(x: Dict[str, Any]) -> Tuple:
        price = x.get("price") if isinstance(x.get("price"), int) else math.inf
        dur = x.get("total_duration_min") or math.inf
        stops_count = x.get("stops_count", 0)
        in_budget = budget_cap is None or (isinstance(price, int) and price <= budget_cap)
        nonstop_bonus = -1 if nonstop_pref and stops_count == 0 else 0
        return (0 if in_budget else 1, price, dur, nonstop_bonus)

    norm.sort(key=score)
    return norm[0]

# --- Public entry point ------------------------------------------------------

def search_best_flight_from_hint(
    hint: str,
    *,
    total_budget_usd: Optional[float] = None,
    currency: str = "USD",
    gl: str = "ca",   # user is in Canada
    hl: str = "en",
) -> Dict[str, Any]:
    parsed = parse_flight_hint(hint)
    if not all([parsed["origin"], parsed["dest"], parsed["outbound_date"], parsed["return_date"]]):
        raise ValueError(f"Unable to parse origin/dest/dates from hint: {hint}")

    # If caller gave total trip budget, assume 1/4 for flights (per your prompt design)
    if total_budget_usd and not parsed.get("max_price"):
        parsed["max_price"] = int(total_budget_usd / 4)

    data = serpapi_flights(parsed, currency=currency, gl=gl, hl=hl)

    best = pick_best_flight(
        data,
        budget_cap=parsed.get("max_price"),
        nonstop_pref=(parsed.get("stops") == 1),
        currency=currency,
    )

    return {
        "query_used": parsed,
        "best_flight": best,
        "raw": {
            "search_metadata": data.get("search_metadata"),
            "price_insights": data.get("price_insights"),    # available when Google shows it :contentReference[oaicite:9]{index=9}
        },
    }

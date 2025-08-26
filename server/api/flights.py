# api/flights.py
import os
import re
import json
import math
import requests
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

def _get_serpapi_key() -> str:
    load_dotenv()
    key = os.getenv("SERPAPI_API_KEY")
    if not key:
        print("[flights] ERROR: SERPAPI_API_KEY is missing")
        raise RuntimeError("Missing SERPAPI_API_KEY")
    return key

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"

# --- Regexes ---------------------------------------------------------------
IATA_RE = re.compile(r"\b([A-Z]{3})\b")
DATE_RANGE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*(?:to|-|–|—)\s*(\d{4}-\d{2}-\d{2})")
PAX_RE = re.compile(r"(\d+)\s*(?:pax|guests?|traveler|travelers)\b", re.I)
CLASS_RE = re.compile(r"\b(economy|premium economy|business|first)\b", re.I)
NONSTOP_RE = re.compile(r"\b(non[-\s]?stop|direct only)\b", re.I)
STOPS_RE = re.compile(r"\b(\d)\s*stop(s)?\b", re.I)
ARROW_SPLIT_RE = re.compile(r"\b([A-Z]{3})\s*(?:->|to|—|–)\s*([A-Z]{3})\b")

TRAVEL_CLASS_MAP = {
    "economy": 1,
    "premium economy": 2,
    "business": 3,
    "first": 4,
}

# Common IATA codes for major cities
COMMON_IATA_CODES = {
    "toronto": "YYZ", "toronto canada": "YYZ", "toronto ontario": "YYZ",
    "new york": "JFK", "new york usa": "JFK", "new york ny": "JFK", "new york city": "JFK",
    "miami": "MIA", "miami fl": "MIA", "miami florida": "MIA",
    "athens": "ATH", "athens greece": "ATH",
    "london": "LHR", "london uk": "LHR", "london england": "LHR",
    "paris": "CDG", "paris france": "CDG",
    "madrid": "MAD", "madrid spain": "MAD",
    "rome": "FCO", "rome italy": "FCO",
    "berlin": "BER", "berlin germany": "BER",
    "tokyo": "NRT", "tokyo japan": "NRT",
    "beijing": "PEK", "beijing china": "PEK",
    "sydney": "SYD", "sydney australia": "SYD",
    "mumbai": "BOM", "mumbai india": "BOM",
    "los angeles": "LAX", "los angeles ca": "LAX", "los angeles california": "LAX",
    "chicago": "ORD", "chicago il": "ORD", "chicago illinois": "ORD",
    "san francisco": "SFO", "san francisco ca": "SFO", "san francisco california": "SFO",
    "amsterdam": "AMS", "amsterdam netherlands": "AMS",
    "barcelona": "BCN", "barcelona spain": "BCN",
    "milan": "MXP", "milan italy": "MXP",
    "munich": "MUC", "munich germany": "MUC",
    "vienna": "VIE", "vienna austria": "VIE",
    "prague": "PRG", "prague czech republic": "PRG",
    "budapest": "BUD", "budapest hungary": "BUD",
    "warsaw": "WAW", "warsaw poland": "WAW",
    "stockholm": "ARN", "stockholm sweden": "ARN",
    "oslo": "OSL", "oslo norway": "OSL",
    "copenhagen": "CPH", "copenhagen denmark": "CPH",
    "helsinki": "HEL", "helsinki finland": "HEL",
    "dublin": "DUB", "dublin ireland": "DUB",
    "edinburgh": "EDI", "edinburgh scotland": "EDI",
    "glasgow": "GLA", "glasgow scotland": "GLA",
    "manchester": "MAN", "manchester uk": "MAN",
    "birmingham": "BHX", "birmingham uk": "BHX",
    "bristol": "BRS", "bristol uk": "BRS",
    "newcastle": "NCL", "newcastle uk": "NCL",
    "belfast": "BFS", "belfast northern ireland": "BFS",
    "cork": "ORK", "cork ireland": "ORK"
}

def _coalesce(*vals):
    for v in vals:
        if v is not None:
            return v
    return None

def parse_flight_hint(hint: str) -> Dict[str, Any]:
    """
    Parse a compact LLM hint like:
      "YYZ->ATH 2025-08-26 to 2025-09-01 2 pax economy nonstop <= $1250"
    Returns structured params for SerpAPI.
    """
    print(f"[flights] parse_flight_hint: raw hint: {hint!r}")
    hint = (hint or "").strip()
    if not hint:
        raise ValueError("Empty flight hint")

    # 1) origin & destination (prefer explicit IATA arrow pattern)
    od = ARROW_SPLIT_RE.search(hint)
    origin, dest = (od.group(1), od.group(2)) if od else (None, None)

    # Fallback: first two IATA codes anywhere
    if not (origin and dest):
        codes = IATA_RE.findall(hint)
        if len(codes) >= 2:
            origin, dest = codes[0], codes[1]
    
    # 2) If still no IATA codes, try to extract city names and convert them
    if not (origin and dest):
        # Look for city names in the format "City Country" or "City"
        # Split by arrow and extract the first two significant words/phrases
        parts = hint.split('->')
        if len(parts) >= 2:
            # Extract origin (before arrow)
            origin_part = parts[0].strip()
            # Extract destination (after arrow)
            dest_part = parts[1].strip()
            
            # Clean up and extract city names
            origin_city = re.sub(r'\d+.*$', '', origin_part).strip()  # Remove dates and numbers
            dest_city = re.sub(r'\d+.*$', '', dest_part).strip()  # Remove dates and numbers
            
            print(f"[flights] Extracted city names: origin='{origin_city}', dest='{dest_city}'")
            
            # Try multiple variations of the city names
            origin = _city_to_iata_best_effort(origin_city)
            if not origin:
                # Try without state/country codes
                origin_clean = re.sub(r'\b[A-Z]{2}\b', '', origin_city).strip()
                if origin_clean != origin_city:
                    print(f"[flights] Trying cleaned origin: '{origin_clean}'")
                    origin = _city_to_iata_best_effort(origin_clean)
            
            dest = _city_to_iata_best_effort(dest_city)
            if not dest:
                # Try without state/country codes
                dest_clean = re.sub(r'\b[A-Z]{2}\b', '', dest_city).strip()
                if dest_clean != dest_city:
                    print(f"[flights] Trying cleaned destination: '{dest_clean}'")
                    dest = _city_to_iata_best_effort(dest_clean)
            
            print(f"[flights] Converted to IATA: {origin_city} -> {origin}, {dest_city} -> {dest}")

    # 3) dates (ISO only)
    dmatch = DATE_RANGE_RE.search(hint)
    outbound_date, return_date = (dmatch.group(1), dmatch.group(2)) if dmatch else (None, None)

    # 4) pax
    pax = 1
    pm = PAX_RE.search(hint)
    if pm:
        pax = max(1, int(pm.group(1)))

    # 5) class
    tclass = 1  # default economy
    cm = CLASS_RE.search(hint)
    if cm:
        tclass = TRAVEL_CLASS_MAP.get(cm.group(1).lower(), 1)

    # 6) stops
    # 0=any; 1=nonstop; 2=<=1 stop; 3=<=2 stops
    stops = 0
    if NONSTOP_RE.search(hint):
        stops = 1
    else:
        sm = STOPS_RE.search(hint)
        if sm:
            n = int(sm.group(1))
            stops = 1 if n == 0 else min(3, n + 1)

    # 7) price cap
    max_price = None
    mp = re.search(r"(?:<=|<=?\s*|\bmax\b|\$)\s*\$?\s*([0-9][0-9,]*)", hint, re.I)
    if mp:
        max_price = int(mp.group(1).replace(",", ""))

    parsed = {
        "origin": origin,
        "dest": dest,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "adults": pax,
        "travel_class": tclass,
        "stops": stops,
        "max_price": max_price,
    }
    print(f"[flights] parse_flight_hint: parsed: {json.dumps(parsed, indent=2)}")
    return parsed

def _city_to_iata_best_effort(text: Optional[str]) -> Optional[str]:
    """
    If text is IATA, return as-is. Else try local map, then SerpAPI best-effort resolver.
    """
    if not text:
        return None
    text_stripped = text.strip()
    print(f"[flights] _city_to_iata_best_effort: trying to resolve '{text_stripped}'")
    
    if IATA_RE.fullmatch(text_stripped):
        print(f"[flights] _city_to_iata_best_effort: '{text_stripped}' is already IATA")
        return text_stripped

    # Try local quick map with multiple variations
    key = text_stripped.lower()
    if key in COMMON_IATA_CODES:
        print(f"[flights] city->IATA (local): {text_stripped} -> {COMMON_IATA_CODES[key]}")
        return COMMON_IATA_CODES[key]
    
    # Try without state/country codes
    clean_key = re.sub(r'\b[A-Z]{2}\b', '', key).strip()
    if clean_key != key and clean_key in COMMON_IATA_CODES:
        print(f"[flights] city->IATA (local, cleaned): {text_stripped} -> {COMMON_IATA_CODES[clean_key]}")
        return COMMON_IATA_CODES[clean_key]

    # SerpAPI best-effort (not guaranteed) - only for unknown cities
    print(f"[flights] city->IATA (serpapi resolver): trying to resolve {text_stripped!r}")
    try:
        api_key = _get_serpapi_key()
        resp = requests.get(
            SERPAPI_SEARCH_URL,
            params={
                "engine": "google_flights",
                "api_key": api_key,
                "departure_id": text_stripped,
                "arrival_id": text_stripped,
                "output": "json",
                "json_restrictor": "airports[].{departure[].airport.id,arrival[].airport.id}",
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
                        print(f"[flights] city->IATA (serpapi): {text_stripped} -> {cand}")
                        return cand
    except Exception as e:
        print(f"[flights] resolver exception: {e}")
    print(f"[flights] city->IATA: failed to resolve {text_stripped!r}")
    return None

def serpapi_flights(params: Dict[str, Any], currency: str = "USD", gl: str = "ca", hl: str = "en") -> Dict[str, Any]:
    """
    Call SerpAPI Google Flights and return JSON with retry logic.
    """
    api_key = _get_serpapi_key()

    dep = params.get("origin")
    arr = params.get("dest")
    out_d = params.get("outbound_date")
    ret_d = params.get("return_date")

    # Validate essentials early
    if not out_d or not ret_d:
        raise ValueError(f"Missing ISO dates in params: {params}")
    if not dep or not arr:
        raise ValueError(f"Missing origin/dest in params: {params}")

    # Resolve non-IATA to IATA
    dep_id = _city_to_iata_best_effort(dep)
    arr_id = _city_to_iata_best_effort(arr)
    if not dep_id or not arr_id:
        raise ValueError(f"Could not resolve IATA codes: origin={dep!r}->{dep_id!r}, dest={arr!r}->{arr_id!r}")

    q = {
        "engine": "google_flights",
        "api_key": api_key,
        "departure_id": dep_id,
        "arrival_id": arr_id,
        "outbound_date": out_d,
        "return_date": ret_d,
        "adults": params.get("adults", 1),
        "travel_class": params.get("travel_class", 1),
        "stops": params.get("stops", 0),  # 1 = nonstop; 0 = any; etc.
        "type": 1,                        # 1 = round trip
        "currency": currency,
        "gl": gl,
        "hl": hl,
        "sort_by": 1,                     # 1 = "Top flights"
        "deep_search": "true",
        "output": "json",
    }
    if params.get("max_price") is not None:
        q["max_price"] = params["max_price"]

    print(f"[flights] serpapi_flights: request params: {json.dumps(q, indent=2)}")

    # Retry logic for SerpAPI
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(SERPAPI_SEARCH_URL, params=q, timeout=60)
            data = resp.json()
            
            if data.get("error"):
                error_msg = data['error']
                print(f"[flights] SerpAPI ERROR (attempt {attempt + 1}/{max_retries}): {error_msg}")
                
                # If it's a temporary error, retry
                if "try again later" in error_msg.lower() or "temporary" in error_msg.lower():
                    if attempt < max_retries - 1:
                        print(f"[flights] Retrying in 2 seconds...")
                        import time
                        time.sleep(2)
                        continue
                
                # If it's a permanent error or we've exhausted retries
                raise RuntimeError(f"SerpAPI error: {error_msg}")
            
            print(f"[flights] serpapi_flights: got response keys: {list(data.keys())}")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"[flights] Request ERROR (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"[flights] Retrying in 2 seconds...")
                import time
                time.sleep(2)
                continue
            raise
        except Exception as e:
            print(f"[flights] ERROR: Non-JSON response: status={resp.status_code}, text={resp.text[:500]}")
            if attempt < max_retries - 1:
                print(f"[flights] Retrying in 2 seconds...")
                import time
                time.sleep(2)
                continue
            resp.raise_for_status()
            raise

    # This should never be reached, but just in case
    raise RuntimeError("SerpAPI request failed after all retries")

def _normalize_flight_item(item: Dict[str, Any], currency: str) -> Dict[str, Any]:
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
        "departure_token": item.get("departure_token"),
        "booking_token": item.get("booking_token"),
    }

def pick_best_flight(data: Dict[str, Any], budget_cap: Optional[int] = None, nonstop_pref: Optional[bool] = None, currency: str = "USD") -> Optional[Dict[str, Any]]:
    candidates = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    print(f"[flights] pick_best_flight: candidates={len(candidates)} (best={len(data.get('best_flights') or [])}, other={len(data.get('other_flights') or [])})")
    if not candidates:
        return None

    norm = [_normalize_flight_item(c, currency) for c in candidates]

    def score(x: Dict[str, Any]) -> Tuple:
        price = x.get("price") if isinstance(x.get("price"), int) else math.inf
        dur = x.get("total_duration_min") or math.inf
        stops_count = x.get("stops_count", 0)
        in_budget = budget_cap is None or (isinstance(price, int) and price <= budget_cap)
        nonstop_bonus = -1 if nonstop_pref and stops_count == 0 else 0
        return (0 if in_budget else 1, price, dur, nonstop_bonus)

    norm.sort(key=score)
    print(f"[flights] pick_best_flight: best={json.dumps(norm[0], indent=2)[:800]}")
    return norm[0]

def search_best_flight_from_hint(
    hint: str,
    *,
    total_budget_usd: Optional[float] = None,
    currency: str = "USD",
    gl: str = "ca",
    hl: str = "en",
) -> Dict[str, Any]:
    print(f"[flights] search_best_flight_from_hint: hint={hint!r}, total_budget_usd={total_budget_usd}")
    parsed = parse_flight_hint(hint)

    # Validate minimal parsed fields before network call
    missing = [k for k in ["origin", "dest", "outbound_date", "return_date"] if not parsed.get(k)]
    if missing:
        raise ValueError(f"Unable to parse required fields from hint (missing: {missing}). Hint was: {hint!r}")

    if total_budget_usd and not parsed.get("max_price"):
        parsed["max_price"] = int(total_budget_usd / 4)
        print(f"[flights] applying budget cap from total_budget_usd: max_price={parsed['max_price']}")

    try:
        data = serpapi_flights(parsed, currency=currency, gl=gl, hl=hl)
        best = pick_best_flight(
            data,
            budget_cap=parsed.get("max_price"),
            nonstop_pref=(parsed.get("stops") == 1),
            currency=currency,
        )
        
        result = {
            "query_used": parsed,
            "best_flight": best,
            "raw": {
                "search_metadata": data.get("search_metadata"),
                "price_insights": data.get("price_insights"),
            },
        }
        print(f"[flights] search_best_flight_from_hint: result keys: {list(result.keys())}")
        return result
        
    except Exception as e:
        print(f"[flights] SerpAPI failed, creating fallback flight: {e}")
        
        # Create a fallback flight structure
        fallback_flight = {
            "price": parsed.get("max_price", 800),
            "currency": currency,
            "total_duration_min": 480,  # 8 hours default
            "stops_count": 1,
            "legs": [
                {
                    "airline": "Multiple Airlines",
                    "flight_number": "N/A",
                    "travel_class": "Economy",
                    "departure": {
                        "airport_id": parsed.get("origin"),
                        "time": f"{parsed.get('outbound_date')} 10:00",
                    },
                    "arrival": {
                        "airport_id": parsed.get("dest"),
                        "time": f"{parsed.get('outbound_date')} 18:00",
                    },
                    "duration_min": 480,
                }
            ],
            "departure_token": None,
            "booking_token": None,
        }
        
        result = {
            "query_used": parsed,
            "best_flight": fallback_flight,
            "raw": {
                "search_metadata": {"status": "fallback"},
                "price_insights": None,
            },
            "fallback": True,
        }
        print(f"[flights] search_best_flight_from_hint: fallback result created")
        return result

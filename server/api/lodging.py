# api/lodging_amadeus.py
from amadeus import Client, ResponseError, Location
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import os
import re

load_dotenv()

AMADEUS = Client(
    client_id=os.getenv("AMAD_ID"),
    client_secret=os.getenv("AMAD_SECRET"),
)

def _nights(check_in: str, check_out: str) -> int:
    d1 = datetime.strptime(check_in, "%Y-%m-%d")
    d2 = datetime.strptime(check_out, "%Y-%m-%d")
    return max(1, (d2 - d1).days)

def _parse_lodging_hint(hint: str) -> Tuple[str, str, str, int]:
    if not isinstance(hint, str) or not hint.strip():
        raise ValueError("Invalid lodging hint")

    m = re.search(r"(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})", hint)
    if not m:
        raise ValueError(f"Could not parse dates from lodging hint: {hint}")
    check_in, check_out = m.group(1), m.group(2)

    adults = 2
    m2 = re.search(r"(\d+)\s*(guests|people|pax)?", hint)
    if m2:
        try:
            adults = int(m2.group(1))
        except Exception:
            pass

    dm = re.search(r"^(.*?)\s+hotels\b", hint, flags=re.IGNORECASE)
    if dm:
        destination = dm.group(1).strip()
    else:
        destination = hint.split(check_in)[0].strip()

    if not destination:
        raise ValueError(f"Could not parse destination from lodging hint: {hint}")

    return destination, check_in, check_out, adults

def _get_city_code(destination: str) -> Optional[str]:
    try:
        # Prefer CITY subtype
        res = AMADEUS.reference_data.locations.get(
            keyword=destination, subType=Location.CITY
        )
        for item in res.data or []:
            code = item.get("iataCode")
            if code:
                return code
    except ResponseError:
        pass

    # Fallback: try AIRPORT; return its iataCode if found (often city code == airport code)
    try:
        res = AMADEUS.reference_data.locations.get(
            keyword=destination, subType=Location.AIRPORT
        )
        for item in res.data or []:
            code = item.get("iataCode")
            if code:
                return code
    except ResponseError:
        pass

    return None

def _best_offer(offers: List[Dict[str, Any]], nights_count: int) -> Optional[Dict[str, Any]]:
    candidates = []
    for block in offers:
        hotel = block.get("hotel", {})
        hname = hotel.get("name")
        rating = None
        # 'rating' can be string like "4" or "4.5"
        r = hotel.get("rating") or hotel.get("ratingValue")
        try:
            rating = float(r) if r is not None else None
        except Exception:
            rating = None

        for off in block.get("offers", []):
            price_total = None
            currency = None
            try:
                price_total = float(off.get("price", {}).get("total"))
                currency = off.get("price", {}).get("currency")
            except Exception:
                continue

            nightly = price_total / max(1, nights_count)
            candidates.append({
                "hotel_name": hname,
                "rating": rating,
                "price_total": price_total,
                "currency": currency,
                "price_per_night": nightly,
                "check_in": off.get("checkInDate"),
                "check_out": off.get("checkOutDate"),
                "room": off.get("room", {}),
                "boardType": off.get("boardType"),
                "offer_id": off.get("id"),
                "raw_offer": off,
                "raw_hotel": hotel,
            })

    if not candidates:
        return None

    # Sort by total price asc, then rating desc
    candidates.sort(key=lambda x: (x["price_total"], -(x["rating"] or 0.0)))
    return candidates[0]

def search_best_lodging_from_hint(
    hint: str,
    currency: str = "USD",
    max_price_per_night: Optional[float] = None,
    min_rating: Optional[float] = None,
) -> Dict[str, Any]:
    destination, check_in, check_out, adults = _parse_lodging_hint(hint)
    city_code = _get_city_code(destination)
    if not city_code:
        return {
            "source": "amadeus",
            "error": f"Could not resolve city code for '{destination}'",
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "adults": adults,
            "best": None,
            "candidates": [],
        }

    nights_count = _nights(check_in, check_out)

    try:
        # SDK: GET /v3/shopping/hotel-offers
        resp = AMADEUS.shopping.hotel_offers.get(
            cityCode=city_code,
            checkInDate=check_in,
            checkOutDate=check_out,
            adults=adults,
            currency=currency,
            roomQuantity=1,
            # You can add view/amenities filters with a separate flow (by_hotels + hotelIds)
        )
        data = resp.data or []
    except ResponseError as e:
        return {
            "source": "amadeus",
            "error": str(e),
            "destination": destination,
            "city_code": city_code,
            "check_in": check_in,
            "check_out": check_out,
            "adults": adults,
            "best": None,
            "candidates": [],
        }

    # Optional filtering before picking best
    filtered: List[Dict[str, Any]] = []
    for block in data:
        hotel = block.get("hotel", {})
        r = hotel.get("rating") or hotel.get("ratingValue")
        try:
            rating_val = float(r) if r is not None else None
        except Exception:
            rating_val = None

        offers_ok = []
        for off in block.get("offers", []):
            try:
                total = float(off.get("price", {}).get("total"))
                nightly = total / nights_count
            except Exception:
                continue
            if max_price_per_night is not None and nightly > max_price_per_night:
                continue
            offers_ok.append(off)

        if not offers_ok:
            continue
        if min_rating is not None and rating_val is not None and rating_val < min_rating:
            continue

        # keep only allowed offers for this hotel
        filtered.append({**block, "offers": offers_ok})

    chosen = _best_offer(filtered or data, nights_count)

    # Build compact payload
    result = {
        "source": "amadeus",
        "destination": destination,
        "city_code": city_code,
        "check_in": check_in,
        "check_out": check_out,
        "adults": adults,
        "nights": nights_count,
        "best": None,
        "candidates": [],
    }

    if chosen:
        result["best"] = {
            "hotel_name": chosen["hotel_name"],
            "rating": chosen["rating"],
            "price_total": chosen["price_total"],
            "price_per_night": chosen["price_per_night"],
            "currency": chosen["currency"],
            "check_in": chosen["check_in"],
            "check_out": chosen["check_out"],
            "boardType": chosen["boardType"],
            "offer_id": chosen["offer_id"],
            # You can book by passing this offer_id to Amadeus /v3/booking/hotel-bookings (separate flow).
        }

        # Up to 5 alternatives for UI
        # Reuse _best_offer sort by re-computing candidates
        # (We already sorted in _best_offer; do another pass here)
        # Flatten top candidates again:
        flat: List[Dict[str, Any]] = []
        for block in (filtered or data):
            hotel = block.get("hotel", {})
            hname = hotel.get("name")
            r = hotel.get("rating") or hotel.get("ratingValue")
            try:
                rating_val = float(r) if r is not None else None
            except Exception:
                rating_val = None
            for off in block.get("offers", []):
                try:
                    total = float(off.get("price", {}).get("total"))
                    cur = off.get("price", {}).get("currency")
                    nightly = total / nights_count
                except Exception:
                    continue
                flat.append({
                    "hotel_name": hname,
                    "rating": rating_val,
                    "price_total": total,
                    "price_per_night": nightly,
                    "currency": cur,
                    "offer_id": off.get("id"),
                })
        flat.sort(key=lambda x: (x["price_total"], -(x["rating"] or 0.0)))
        result["candidates"] = flat[:5]

    return result

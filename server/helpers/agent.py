from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

from dotenv import load_dotenv
import os
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
import time

# ------------ Env & LLM ------------
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Use a more stable model
LLM_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

llm = ChatGoogleGenerativeAI(
    model=LLM_MODEL,
    temperature=0.1,  # Lower temperature for more consistent output
    max_output_tokens=2048,
    api_key=GOOGLE_API_KEY,
)

# ------------ Date parsing helpers ------------
def to_iso_date(s: str) -> Optional[str]:
    """
    Try multiple common formats. Extend as needed.
    Examples that will parse:
      - '2025-08-26'
      - 'Aug 26 2025'
      - 'August 26, 2025'
      - '26 Aug 2025'
    """
    if not s:
        return None
    s = s.strip()

    fmts = [
        "%Y-%m-%d",
        "%b %d %Y",      # Aug 26 2025
        "%B %d, %Y",     # August 26, 2025
        "%d %b %Y",      # 26 Aug 2025
        "%d %B %Y",      # 26 August 2025
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return None

# ------------ Simplified Prompt ------------
breakdown_template = """You are a travel planning assistant. Convert the user's trip details into API-ready search queries.

Trip Details:
- Departure: {departure}
- Destination: {destination}
- Budget: {budget}
- Dates: {startISO} to {endISO}
- Travelers: {travelers}
- Interests: {interests}

Generate search queries for:
1. Flights: Round-trip from departure to destination (MUST use IATA airport codes)
2. Lodging: Hotels in destination
3. Activities: Based on interests

CRITICAL: For flights, you MUST convert city names to IATA airport codes. Here are the most common conversions:

Major US Cities:
- Miami FL → MIA
- New York NY → JFK
- Los Angeles CA → LAX
- Chicago IL → ORD
- San Francisco CA → SFO

Major International Cities:
- Toronto Canada → YYZ
- London UK → LHR
- Paris France → CDG
- Madrid Spain → MAD
- Athens Greece → ATH
- Rome Italy → FCO
- Berlin Germany → BER
- Tokyo Japan → NRT
- Beijing China → PEK
- Sydney Australia → SYD
- Mumbai India → BOM
- Amsterdam Netherlands → AMS
- Barcelona Spain → BCN
- Milan Italy → MXP
- Munich Germany → MUC
- Vienna Austria → VIE
- Prague Czech Republic → PRG
- Budapest Hungary → BUD
- Warsaw Poland → WAW
- Stockholm Sweden → ARN
- Oslo Norway → OSL
- Copenhagen Denmark → CPH
- Helsinki Finland → HEL
- Dublin Ireland → DUB
- Edinburgh Scotland → EDI
- Glasgow Scotland → GLA
- Manchester UK → MAN
- Birmingham UK → BHX
- Bristol UK → BRS
- Newcastle UK → NCL
- Belfast Northern Ireland → BFS
- Cork Ireland → ORK

IMPORTANT: 
1. ALWAYS convert city names to IATA codes for flights
2. Use the exact format: "IATA_CODE -> IATA_CODE"
3. If you don't know the IATA code, use the city name and let the system handle it

Return ONLY valid JSON in this exact format:
{{
  "flights": {{
    "serpapi": [
      "IATA_CODE -> IATA_CODE {startISO} to {endISO} {travelers} pax economy"
    ]
  }},
  "lodging": {{
    "Expedia": [
      "{destination} hotels {startISO} to {endISO} {travelers} guests"
    ]
  }},
  "transportation": {{
    "public_transit": [
      "{destination} public transit {startISO} to {endISO}"
    ],
    "uber": [
      "{destination} airport transfer {startISO} to {endISO}"
    ],
    "car_rental": [
      "{destination} car rental {startISO} to {endISO}"
    ]
  }},
  "activities": {{
    "eventbrite": [
      "{destination} {interests} {startISO} to {endISO}"
    ],
    "tripadvisor": [
      "{destination} attractions {interests} {startISO} to {endISO}"
    ]
  }},
  "food": {{
    "yelp": [
      "{destination} restaurants {startISO} to {endISO}"
    ]
  }}
}}

Important: Return ONLY the JSON, no other text or explanations."""

breakdown_prompt = PromptTemplate(
    input_variables=[
        "departure", "destination", "budget", "startISO", "endISO", "travelers", "interests"
    ],
    template=breakdown_template
)

# ------------ Utilities ------------
def force_dates_into_queries(data: Dict[str, Any], start_iso: str, end_iso: str) -> Dict[str, Any]:
    """
    Ensure every query string includes the ISO date range. If missing,
    append " {start_iso} to {end_iso}" at the end.
    """
    def ensure_list_with_dates(lst: List[str]) -> List[str]:
        out = []
        for q in lst:
            if q is None:
                continue
            q_str = str(q)
            if (start_iso not in q_str) or (end_iso not in q_str):
                q_str = f"{q_str} {start_iso} to {end_iso}"
            out.append(q_str.strip())
        return out

    # Walk expected structure
    if "flights" in data and "serpapi" in data["flights"]:
        data["flights"]["serpapi"] = ensure_list_with_dates(data["flights"]["serpapi"])

    if "lodging" in data and "Expedia" in data["lodging"]:
        data["lodging"]["Expedia"] = ensure_list_with_dates(data["lodging"]["Expedia"])

    if "transportation" in data:
        t = data["transportation"]
        for key in ["public_transit", "uber", "car_rental"]:
            if key in t and isinstance(t[key], list):
                t[key] = ensure_list_with_dates(t[key])

    if "activities" in data:
        a = data["activities"]
        for key in ["eventbrite", "tripadvisor"]:
            if key in a and isinstance(a[key], list):
                a[key] = ensure_list_with_dates(a[key])

    if "food" in data and "yelp" in data["food"]:
        data["food"]["yelp"] = ensure_list_with_dates(data["food"]["yelp"])

    return data

def ensure_iata_codes_in_flights(data: Dict[str, Any], departure: str, destination: str) -> Dict[str, Any]:
    """
    Post-process flight queries to ensure IATA codes are used.
    If the LLM didn't convert city names to IATA codes, do it here.
    """
    if "flights" not in data or "serpapi" not in data["flights"]:
        return data
    
    # Common IATA codes mapping
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
    
    def get_iata_code(city_name: str) -> str:
        """Convert city name to IATA code"""
        if not city_name:
            return city_name
        
        # Check if it's already an IATA code (3 uppercase letters)
        import re
        if re.match(r'^[A-Z]{3}$', city_name):
            return city_name
        
        # Try to find in our mapping
        city_lower = city_name.lower().strip()
        return COMMON_IATA_CODES.get(city_lower, city_name)
    
    def convert_flight_query(query: str) -> str:
        """Convert city names to IATA codes in flight query"""
        if not query or "->" not in query:
            return query
        
        # Split by arrow
        parts = query.split("->")
        if len(parts) != 2:
            return query
        
        origin_part = parts[0].strip()
        dest_part = parts[1].strip()
        
        # Extract city names (remove dates, numbers, etc.)
        import re
        origin_city = re.sub(r'\d+.*$', '', origin_part).strip()
        dest_city = re.sub(r'\d+.*$', '', dest_part).strip()
        
        # Convert to IATA codes
        origin_iata = get_iata_code(origin_city)
        dest_iata = get_iata_code(dest_city)
        
        # Reconstruct query
        new_query = f"{origin_iata} -> {dest_iata}"
        
        # Add back the rest of the query (dates, passengers, etc.)
        rest_of_query = dest_part[len(dest_city):].strip()
        if rest_of_query:
            new_query += " " + rest_of_query
        
        return new_query
    
    # Process each flight query
    flight_queries = data["flights"]["serpapi"]
    processed_queries = []
    
    for query in flight_queries:
        if query and isinstance(query, str):
            processed_query = convert_flight_query(query)
            processed_queries.append(processed_query)
            if processed_query != query:
                print(f"[agent] Converted flight query: {query} -> {processed_query}")
        else:
            processed_queries.append(query)
    
    data["flights"]["serpapi"] = processed_queries
    return data

def invoke_with_retry(chain, inputs: dict, attempts: int = 3, backoff_sec: float = 2.0):
    """
    Retry for occasional upstream 500s with better error handling.
    """
    last_err = None
    for i in range(1, attempts + 1):
        try:
            print(f"[TripPilot] LLM attempt {i}/{attempts}")
            return chain.invoke(inputs)
        except Exception as e:
            last_err = e
            print(f"[TripPilot] LLM attempt {i} failed: {e}")
            
            # If it's a clear API error, wait longer
            if "InternalServerError" in str(e) or "500" in str(e):
                wait_time = backoff_sec * (i ** 1.5)  # Exponential backoff
                print(f"[TripPilot] API error detected, waiting {wait_time}s before retry")
                time.sleep(wait_time)
            else:
                # For other errors, shorter wait
                time.sleep(backoff_sec * i)
                
    print(f"[TripPilot] All {attempts} LLM attempts failed")
    raise last_err

# ------------ Main functions ------------
def test_llm_connection():
    """Test if the LLM is working with a simple prompt"""
    try:
        test_prompt = PromptTemplate(
            input_variables=["test"],
            template="Say 'Hello {test}' and nothing else."
        )
        test_chain = test_prompt | llm
        response = test_chain.invoke({"test": "World"})
        content = response.content if hasattr(response, "content") else str(response)
        print(f"[TripPilot] LLM test successful: {content}")
        return True
    except Exception as e:
        print(f"[TripPilot] LLM test failed: {e}")
        return False

def create_fallback_plan(trip: dict, start_iso: str, end_iso: str) -> dict:
    """Create a basic fallback plan when LLM fails"""
    departure = trip.get("departure", "")
    destination = trip.get("destination", "")
    travelers = trip.get("travelers", "")
    interests = trip.get("interests", "")
    
    # Simple IATA code mapping for common cities
    def get_iata_code(city_name):
        city_lower = city_name.lower()
        iata_map = {
            "toronto": "YYZ", "toronto canada": "YYZ", "toronto ontario": "YYZ",
            "new york": "JFK", "new york usa": "JFK", "new york ny": "JFK", "new york city": "JFK",
            "miami": "MIA", "miami fl": "MIA", "miami florida": "MIA",
            "madrid": "MAD", "madrid spain": "MAD",
            "athens": "ATH", "athens greece": "ATH",
            "london": "LHR", "london uk": "LHR", "london england": "LHR",
            "paris": "CDG", "paris france": "CDG",
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
        return iata_map.get(city_lower, city_name)  # Return original if not found
    
    departure_iata = get_iata_code(departure)
    destination_iata = get_iata_code(destination)
    
    return {
        "flights": {
            "serpapi": [
                f"{departure_iata}->{destination_iata} {start_iso} to {end_iso} {travelers} pax economy"
            ]
        },
        "lodging": {
            "Expedia": [
                f"{destination} hotels {start_iso} to {end_iso} {travelers} guests"
            ]
        },
        "transportation": {
            "public_transit": [
                f"{destination} public transit {start_iso} to {end_iso}"
            ],
            "uber": [
                f"{destination} airport transfer {start_iso} to {end_iso}"
            ],
            "car_rental": [
                f"{destination} car rental {start_iso} to {end_iso}"
            ]
        },
        "activities": {
            "eventbrite": [
                f"{destination} {interests} {start_iso} to {end_iso}"
            ],
            "tripadvisor": [
                f"{destination} attractions {interests} {start_iso} to {end_iso}"
            ]
        },
        "food": {
            "yelp": [
                f"{destination} restaurants {start_iso} to {end_iso}"
            ]
        },
        "_meta": {"startISO": start_iso, "endISO": end_iso, "fallback": True}
    }

def breakdown_trip_to_queries(trip: dict) -> dict:
    # 1) Parse dates to ISO
    start_iso = to_iso_date(trip.get("startDate", ""))
    end_iso = to_iso_date(trip.get("endDate", ""))

    # 2) Debug prints (these will show in your server logs)
    print(f"[TripPilot] Parsed ISO dates -> startISO={start_iso}, endISO={end_iso}")

    if not start_iso or not end_iso:
        raise ValueError(f"Could not parse dates to ISO. startDate='{trip.get('startDate')}', endDate='{trip.get('endDate')}'")

    # 3) Build inputs including ISO dates
    llm_inputs = {
        "departure": trip.get("departure", ""),
        "destination": trip.get("destination", ""),
        "budget": trip.get("budget", ""),
        "startISO": start_iso,
        "endISO": end_iso,
        "travelers": trip.get("travelers", ""),
        "interests": trip.get("interests", ""),
    }

    chain = breakdown_prompt | llm

    # 4) Invoke with retry and better error handling
    try:
        response = invoke_with_retry(chain, llm_inputs, attempts=3)
        content = response.content if hasattr(response, "content") else str(response)
        
        print(f"[TripPilot] Raw LLM response: {content[:500]}...")
        
        if not content or content.strip() == "":
            print("[TripPilot] Empty response received from LLM")
            raise ValueError("Empty response from breakdown_chain")
            
    except Exception as e:
        print(f"[TripPilot] Error during LLM invocation: {e}")
        raise ValueError(f"LLM invocation failed: {e}")

    # 5) Extract JSON with better error handling
    content = content.strip()
    if not content.startswith("{"):
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            print(f"[TripPilot] Raw LLM content (no JSON found): {content}")
            raise ValueError("No JSON found in response")
        content = m.group(0)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"[TripPilot] JSON decode error: {e}")
        print(f"[TripPilot] Response content:\n{content}")
        raise ValueError(f"Invalid JSON from breakdown_chain: {content}")

    # 6) Light validation (match the prompt's schema)
    required_top = ["flights", "lodging", "transportation", "activities", "food"]
    for k in required_top:
        if k not in data:
            raise ValueError(f"Missing '{k}' in JSON")

    if "serpapi" not in data["flights"]:
        raise ValueError("Missing 'flights.serpapi' in JSON")

    if "Expedia" not in data["lodging"]:
        raise ValueError("Missing 'lodging.Expedia' in JSON")

    t = data["transportation"]
    for k in ["public_transit", "uber", "car_rental"]:
        _ = t.get(k, [])

    a = data["activities"]
    for k in ["eventbrite", "tripadvisor"]:
        _ = a.get(k, [])

    _ = data["food"].get("yelp", [])

    # 7) Force ISO dates into every query string
    data = force_dates_into_queries(data, start_iso, end_iso)
    
    # 8) Ensure IATA codes are used in flight queries
    data = ensure_iata_codes_in_flights(data, trip.get("departure", ""), trip.get("destination", ""))

    # 9) Optionally attach the ISO dates for your downstream pipeline
    data["_meta"] = {"startISO": start_iso, "endISO": end_iso}

    return data

def generate_travel_plan(trip: dict) -> dict:
    try:
        return breakdown_trip_to_queries(trip)
    except Exception as e:
        print(f"[TripPilot] LLM failed, using fallback plan: {e}")
        # Parse dates for fallback
        start_iso = to_iso_date(trip.get("startDate", ""))
        end_iso = to_iso_date(trip.get("endDate", ""))
        if not start_iso or not end_iso:
            raise ValueError(f"Could not parse dates for fallback. startDate='{trip.get('startDate')}', endDate='{trip.get('endDate')}'")
        return create_fallback_plan(trip, start_iso, end_iso)

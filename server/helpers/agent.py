from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

from dotenv import load_dotenv
import os
import json
import re

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize Gemini LLM with increased token limit
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.2,
    max_output_tokens=4096,  # Increased from 1024
    api_key=GOOGLE_API_KEY
)

# --- Step 1: Breakdown -> API Query Builder ---
# Return concise, keyword-focused queries that your code can drop into each API.
# Provide 2-4 variants per API to increase hit rate. No prose, only JSON.
breakdown_template = """You are a travel planning assistant. Convert the user's trip details into API-ready search queries.
Queries must be short (<=120 chars), keyword-rich, and include location and date range. No extra commentary.

Trip Details:
- Departure: {departure}
- Destination: {destination}
- Budget: {budget}
- Dates: {startDate} to {endDate}
- Travelers: {travelers}
- Accessibility: {accessibility}
- Interests: {interests}
- Notes: {notes}

Derive:
- guests = number of people from "Travelers"
- date range = ISO dates as given: Make sure the dates are in ISO format (YYYY-MM-DD)
- city = main destination city
- For the flights, assume economy class unless specified otherwise and make it round-trip and 1/4 of the total budget
- price hints: if possible infer a per-night cap for lodging and "budget"/"cheap"/"midrange" keywords for activities/food and for all the nights total to 1/4 of the budget
- For Transportation: Determine if public transit, Uber, or car rental is needed based on destination and dates and only include the relevant ones. For example if the user mentions "airport" and "downtown" in the same sentence, include Uber queries.
- include neighborhoods/landmarks if user mentions them
- include accessibility hints (e.g., "wheelchair accessible") when relevant

Return ONLY this JSON (no other text, no trailing commas):
{{
  "flights": {{
    "serpapi": [
      "origin->destination + dates + passengers + cabin class (economy) + non-stop/any"
    ]
  }}, 
  "lodging": {{
    "Expedia": [
      "Destination + area + dates + guests + price cap/night + must-haves (wifi, kitchen, etc.)",
      "another variant..."
    ]
  }},
  "transportation": {{
    "public_transit": [
      "city transit passes or route queries within dates, include zones/airport if mentioned"
    ],
    "uber": [
      "city airport->downtown within dates, passengers, time window keywords"
    ],
    "car_rental": [
      "city car rental dates + pickup/dropoff + class (economy) + drivers age if implied"
    ]
  }},
  "activities": {{
    "eventbrite": [
      "city + interests + date range + free/paid keyword if budget constrained"
    ],
    "tripadvisor": [
      "city top attractions + interests + half-day/full-day + cheap/midrange"
    ]
  }},
  "food": {{
    "yelp": [
      "city + cuisine + neighborhood/landmark + price tier + open now if relevant"
    ]
  }}
}}

Fill the arrays with 2-4 concrete query strings each, customized from the Trip Details.
Use compact keywords and symbols where helpful (e.g., 2 guests, $150/night). No explanations, only JSON.
"""

breakdown_prompt = PromptTemplate(
    input_variables=[
        "departure", "destination", "budget", "startDate", "endDate",
        "travelers", "accessibility", "interests", "notes"
    ],
    template=breakdown_template
)
breakdown_chain = breakdown_prompt | llm

def breakdown_trip_to_queries(trip: dict) -> dict:
    try:
        response = breakdown_chain.invoke(trip)
        content = response.content if hasattr(response, "content") else str(response)

        if not content or content.strip() == "":
            raise ValueError("Empty response from breakdown_chain")

        content = content.strip()
        if not content.startswith("{"):
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if not m:
                raise ValueError("No JSON found in response")
            content = m.group(0)

        data = json.loads(content)

        # Optional: light validation to ensure expected keys exist
        required_top = ["flights","lodging", "transportation", "activities", "food"]
        for k in required_top:
            if k not in data:
                raise ValueError(f"Missing '{k}' in JSON")

        # Ensure subkeys exist
        _ = data["flights"].get("skyscanner", [])
        _ = data["lodging"].get("airbnb", [])
        t = data["transportation"]
        _ = t.get("public_transit", []), t.get("uber", []), t.get("car_rental", [])
        a = data["activities"]
        _ = a.get("eventbrite", []), a.get("tripadvisor", [])
        _ = data["food"].get("yelp", [])

        return data

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response content: {content}")
        raise ValueError(f"Invalid JSON from breakdown_chain: {content}")
    except Exception as e:
        print(f"Breakdown error: {e}")
        raise ValueError(f"Error in breakdown_trip_to_queries: {e}")

def generate_travel_plan(trip: dict) -> dict:
    return breakdown_trip_to_queries(trip)

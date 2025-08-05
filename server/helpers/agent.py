from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from dotenv import load_dotenv

load_dotenv()
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.2,
    max_output_tokens=1024,
    api_key=GOOGLE_API_KEY
)

# --- Step 1: Breakdown Prompt ---
breakdown_template = """You are a travel planning assistant. Given the user's trip details below, break the trip down into the following four components:

1. Lodging (where the user should stay)
2. Transportation (how the user will get around)
3. Activities (things to do, based on interests)
4. Food (local cuisine or specific recommendations — if not specified, suggest local favorites)

Respond strictly in this JSON format:
{{
  "lodging": "...",
  "transportation": "...",
  "activities": "...",
  "food": "..."
}}

Trip Details:
Destination: {destination}
Budget: {budget}
Dates: {startDate} to {endDate}
Travelers: {travelers}
Accessibility: {accessibility}
Interests: {interests}
Notes: {notes}
"""

breakdown_prompt = PromptTemplate(
    input_variables=["destination", "budget", "startDate", "endDate", "travelers", "accessibility", "interests", "notes"],
    template=breakdown_template
)
breakdown_chain = LLMChain(llm=llm, prompt=breakdown_prompt)

# --- Step 2: Final Plan Prompt ---
plan_template = """You are a travel planner AI. Based on the following structured trip breakdown, create a friendly but structured day-by-day itinerary that:
- Includes activities, meals, and rest time.
- Keeps everything within the user's budget.
- Prioritizes the user's accessibility needs and interests.
- Makes the plan exciting and memorable.

Lodging: {lodging}
Transportation: {transportation}
Activities: {activities}
Food: {food}
Budget: {budget}
Dates: {startDate} to {endDate}
Travelers: {travelers}

Return a friendly and clear day-by-day plan:
"""

plan_prompt = PromptTemplate(
    input_variables=["lodging", "transportation", "activities", "food", "budget", "startDate", "endDate", "travelers"],
    template=plan_template
)
plan_chain = LLMChain(llm=llm, prompt=plan_prompt)

def breakdown_trip(trip: dict) -> dict:
    response = breakdown_chain.run(**trip)
    import json
    try:
        return json.loads(response)
    except:
        raise ValueError(f"Invalid JSON from breakdown_chain: {response}")

def generate_travel_plan(trip: dict) -> str:
    breakdown = breakdown_trip(trip)
    return plan_chain.run(
        lodging=breakdown["lodging"],
        transportation=breakdown["transportation"],
        activities=breakdown["activities"],
        food=breakdown["food"],
        budget=trip["budget"],
        startDate=trip["startDate"],
        endDate=trip["endDate"],
        travelers=trip["travelers"]
    )
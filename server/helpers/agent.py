from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

from dotenv import load_dotenv
import os
import json

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

# --- Step 1: Breakdown Prompt (Simplified) ---
breakdown_template = """You are a travel planning assistant. Given the user's trip details, break the trip down into exactly 4 components in JSON format.

Trip Details:
- Destination: {destination}
- Budget: {budget}
- Dates: {startDate} to {endDate}
- Travelers: {travelers}
- Accessibility: {accessibility}
- Interests: {interests}
- Notes: {notes}

Return ONLY this JSON format (no other text):
{{
  "lodging": "brief lodging recommendation",
  "transportation": "brief transportation advice", 
  "activities": "brief activity suggestions",
  "food": "brief food recommendations"
}}"""

breakdown_prompt = PromptTemplate(
    input_variables=["destination", "budget", "startDate", "endDate", "travelers", "accessibility", "interests", "notes"],
    template=breakdown_template
)
breakdown_chain = breakdown_prompt | llm

# --- Step 2: Final Plan Prompt ---
plan_template = """Create a day-by-day travel itinerary based on this breakdown:

Lodging: {lodging}
Transportation: {transportation}
Activities: {activities}
Food: {food}

Trip Details:
- Budget: {budget}
- Dates: {startDate} to {endDate}
- Travelers: {travelers}

Create a friendly, structured day-by-day plan within the budget."""

plan_prompt = PromptTemplate(
    input_variables=["lodging", "transportation", "activities", "food", "budget", "startDate", "endDate", "travelers"],
    template=plan_template
)
plan_chain = plan_prompt | llm

# --- Step 3: Improved Orchestration Functions ---
def breakdown_trip(trip: dict) -> dict:
    try:
        response = breakdown_chain.invoke(trip)
        print("Breakdown response:", response)
        
        # Handle different response types
        content = response.content if hasattr(response, 'content') else str(response)
        
        if not content or content.strip() == '':
            raise ValueError("Empty response from breakdown_chain")
        
        # Try to extract JSON if there's extra text
        content = content.strip()
        if not content.startswith('{'):
            # Look for JSON in the response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            else:
                raise ValueError("No JSON found in response")
        
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response content: {content}")
        raise ValueError(f"Invalid JSON from breakdown_chain: {content}")
    except Exception as e:
        print(f"Breakdown error: {e}")
        raise ValueError(f"Error in breakdown_trip: {e}")

def generate_travel_plan(trip: dict) -> str:
    try:
        breakdown = breakdown_trip(trip)
        response = plan_chain.invoke({
            "lodging": breakdown["lodging"],
            "transportation": breakdown["transportation"],
            "activities": breakdown["activities"],
            "food": breakdown["food"],
            "budget": trip["budget"],
            "startDate": trip["startDate"],
            "endDate": trip["endDate"],
            "travelers": trip["travelers"]
        })
        
        # Handle different response types
        final_plan = response.content if hasattr(response, 'content') else str(response)
        return final_plan
    except Exception as e:
        print(f"Plan generation error: {e}")
        raise RuntimeError(f"Failed to generate final plan. Error: {e}")
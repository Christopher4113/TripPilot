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

template = """You are a travel planner AI. Based on the following trip details, create a short day-by-day plan including activities, estimated budget usage, and how to best accommodate the user's interests and accessibility needs. Make sure all of the hotels, activities, resturaunts and transportation total is within the budget constraints.
The User cannot spend more than the budget provided.

Destination: {destination}
Budget: {budget}
Dates: {startDate} to {endDate}
Travelers: {travelers}
Accessibility: {accessibility}
Interests: {interests}
Notes: {notes}

Output a friendly but structured travel plan:"""

prompt = PromptTemplate(
    input_variables=["destination", "budget", "startDate", "endDate", "travelers", "accessibility", "interests", "notes"],
    template=template
)
chain = LLMChain(llm=llm, prompt=prompt)


def generate_travel_plan(trip: dict) -> str:
    return chain.run(**trip)
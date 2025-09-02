from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from helpers.extractToken import get_current_user
from database.pinecone import add_user_pinecone, index
from helpers.agent import generate_travel_plan, test_llm_connection
from api.flights import search_best_flight_from_hint
from api.lodging import search_best_lodging_from_hint_serpapi
from pydantic import BaseModel

app = FastAPI()
origins = [
    "http://localhost:3000",  # your frontend
    # add more origins if deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Trip(BaseModel):
    destination: str
    departure: str
    budget: str
    startDate: str
    endDate: str
    travelers: str
    accessibility: str
    interests: str
    notes: str

class TripList(BaseModel):
    trips: list[Trip]

@app.get("/")
async def read_root():
    return {"message": "Hello, FastAPI"}

@app.get("/test_llm")
async def test_llm():
    """Test endpoint to check if the LLM is working"""
    try:
        success = test_llm_connection()
        return {"success": success, "message": "LLM test completed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user["user_id"],
        "username": current_user["username"]
    }

@app.post("/register_pinecone_user")
def register_user_in_pinecone(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    username = current_user["username"]
    
    # You can customize this text to represent the user's profile, preferences, etc.
    default_text = f"This is the profile for {username}"

    add_user_pinecone(user_id=user_id, username=username, text=default_text)
    return {"message": f"User {username} registered in Pinecone with ID {user_id}"}

# main.py
@app.get("/test_lodging_serpapi")
def test_lodging_serpapi():
    return search_best_lodging_from_hint_serpapi(
        "MAD hotels 2025-10-01 to 2025-10-08 2 guests 1250 total find the best hotel",
        gl="ca", hl="en", currency_default="EUR"  # override as you prefer
    )


@app.get("/check_user_exists")
def check_user_exists(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    try:
        response = index.fetch(ids=[user_id])
        exists = user_id in response.vectors
        return {"exists": exists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/create_trip")
def create_trip(payload: TripList, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    
    if not payload.trips:
        raise HTTPException(status_code=400, detail="No trips provided")

    try:
        trip_plans = []
        print(f"Received {len(payload.trips)} trip(s) from user {user_id}")
        for i, trip in enumerate(payload.trips):
            trip_dict = trip.dict()
            print(f"Trip {i+1}: {trip_dict}")

            # Call Gemini LLM to generate a plan
            print(f"[create_trip] Generating plan for trip {i+1}...")
            plan = generate_travel_plan(trip_dict)
            print(f"[create_trip] Plan generated successfully for trip {i+1}")
            flight_hints = (
                plan.get("flights", {})
                    .get("serpapi", [])
                or plan.get("flights", {}).get("serpapi", [])  # fallback if needed
            )
            if not flight_hints:
                raise HTTPException(status_code=500, detail="LLM did not return a flights.serpapi hint")

            # 3) Convert budget string like "$1200" or "1200 USD" to a float if you want the 1/4 rule
            total_budget = None
            try:
                # very light parse
                digits = "".join(ch for ch in trip_dict.get("budget", "") if ch.isdigit())
                if digits:
                    total_budget = float(digits)
            except Exception:
                pass

            # 4) Hit SerpAPI & pick best flight
            best_flight = search_best_flight_from_hint(
                flight_hints[0],
                total_budget_usd=total_budget,
                currency="USD",  # or detect from user
                gl="ca",
                hl="en",
            )

            lodging_hints = plan.get("lodging", {}).get("Expedia", [])
            best_lodging = None
            if lodging_hints:
                best_lodging = search_best_lodging_from_hint_serpapi(lodging_hints[0], gl="ca", hl="en")

            trip_plans.append({
                "trip": trip_dict,
                "plan": plan,
                "flight": best_flight,  # <- your UI can show price, legs, duration, etc.
                "lodging": best_lodging,
            })
            print(f"Generated plan for trip {i+1}: {plan}")

        return {"message": "Trips processed successfully", "plans": trip_plans}
    except Exception as e:
        import traceback
        print("[create_trip] EXCEPTION:", repr(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
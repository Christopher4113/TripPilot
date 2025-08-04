from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from helpers.extractToken import get_current_user
from database.pinecone import add_user_pinecone, index
from helpers.agent import generate_travel_plan
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
            plan = generate_travel_plan(trip_dict)
            trip_plans.append({
                "trip": trip_dict,
                "plan": plan
            })

        return {"message": "Trips processed successfully", "plans": trip_plans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
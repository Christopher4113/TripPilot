from fastapi import FastAPI, Depends
from helpers.extractToken import get_current_user
from database.pinecone import add_user_pinecone

app = FastAPI()

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

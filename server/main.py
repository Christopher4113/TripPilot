from fastapi import FastAPI, Depends
from helpers.extractToken import get_current_user

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
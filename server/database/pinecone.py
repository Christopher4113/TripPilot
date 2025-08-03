from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()
import os

# CONFIGURATION
PINECONE_API_KEY =  os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# Init client
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

def add_user_pinecone(user_id: str, username: str, text: str = "default user profile"):
    """Add user to Pinecone index."""
    embed_response = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=[text],
        parameters={"input_type": "query"}
    )

    if not embed_response.data:
        raise ValueError("Embedding failed or returned empty result")

    embedding = embed_response.data[0]["values"]

    index.upsert(vectors=[
        {
            "id": user_id,
            "values": embedding,
            "metadata": {"username": username}
        }
    ])

def get_context_from_pinecone(user_id: str):
    """Fetch user context from Pinecone index."""
    try:
        response = index.fetch(ids=[user_id])
        if user_id in response.vectors:
            return response.vectors[user_id].metadata
        else:
            return None
    except Exception as e:
        raise ValueError(f"Error fetching user context: {str(e)}")
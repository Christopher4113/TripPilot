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
            model="llama-text-embed-v2",  # Use the model from your screenshot
            inputs=[text],
            parameters={"input_type": "query"}
    )
        
    embedding = embed_response.embeddings[0].values  # Adjust depending on your SDK version

    index.upsert(vectors=[
        {
            "id": user_id,
            "values": embedding,
            "metadata": {"username": username}
        }
    ])


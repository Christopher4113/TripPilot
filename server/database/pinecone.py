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

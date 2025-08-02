def add_user_pinecone(user_id: str, username: str, index: str, text: str = "default user profile"):
    """Add user to Pinecone index."""
    embed_response = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=[text],
        parameters={"input_type": "query"}
    )

    print("Embedding response:", embed_response)

    if not embed_response.embeddings:
        raise ValueError("Embedding failed or returned empty result")

    embedding = embed_response.embeddings[0].values

    index.upsert(vectors=[
        {
            "id": user_id,
            "values": embedding,
            "metadata": {"username": username}
        }
    ])

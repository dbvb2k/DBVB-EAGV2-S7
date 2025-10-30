import numpy as np
from app.services.nomic_embed import nomic_embed

def get_embedding(text):
    """Get embedding for the given text using Nomic."""
    try:
        # Get embedding from Nomic
        embedding = nomic_embed.get_embedding(text)
        return np.array(embedding, dtype=np.float32)
    except Exception as e:
        raise Exception(f"Error getting embedding: {str(e)}") 

def normalize_embedding(vec: np.ndarray) -> np.ndarray:
    """L2-normalize an embedding vector."""
    if vec is None:
        return vec
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm
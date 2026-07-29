import numpy as np
from typing import List

from sentence_transformers import SentenceTransformer


class EmbeddingManager:
    """Handles the generation of embedding for chunks using SentenceTransformer"""
    def __init__(self, model_name:str = "all-MiniLM-L6-v2"):
        self.model_name=model_name
        self.model=None
        self._load_model()
        
    def _load_model(self):
        try:
            print(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print(f"Successfully loaded the embedding model with dimensions : {self.model.get_embedding_dimension()}")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
        
    def generate_embeddings(self, document_chunk_texts:List[str])->np.ndarray:
        if not self.model:
            raise ValueError("Model not Loaded")
        print(f"Generating embeddings for {len(document_chunk_texts)} chunks")
        embeddings = self.model.encode(document_chunk_texts, show_progress_bar=True)
        print(f"Generated embeddings with shape: {embeddings.shape}")
        return embeddings
        
    
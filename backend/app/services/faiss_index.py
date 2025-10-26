import faiss
import numpy as np
import json
import os
import logging
from typing import List, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaissIndex:
    def __init__(self, index_path: str):
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.dimension = 768  # nomic-embed-text-v1.5 returns 768-dimensional embeddings
        self.index = None
        self.metadata = {}
        self.initialize()
    
    def initialize(self):
        """Initialize or load the FAISS index and metadata."""
        try:
            if self.index_path.exists() and self.index_path.with_suffix('.json').exists():
                logger.info("Loading existing FAISS index and metadata")
                self.index = faiss.read_index(str(self.index_path))
                with open(self.index_path.with_suffix('.json'), 'r') as f:
                    self.metadata = json.load(f)
            else:
                logger.info("Creating new FAISS index")
                self.index = faiss.IndexFlatL2(self.dimension)
                self.metadata = {}
            
            logger.info(f"Index initialized with {len(self.metadata)} documents")
            
        except Exception as e:
            logger.error(f"Error initializing index: {str(e)}", exc_info=True)
            # Create a new index if loading fails
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = {}
    
    def save(self):
        """Save the current index and metadata to disk."""
        try:
            faiss.write_index(self.index, str(self.index_path))
            with open(self.index_path.with_suffix('.json'), 'w') as f:
                json.dump(self.metadata, f)
            logger.info(f"Index saved with {len(self.metadata)} documents")
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}", exc_info=True)
            raise
    
    def add(self, embedding: np.ndarray, document: Dict[str, Any]) -> str:
        """Add a document to the index."""
        try:
            # Add embedding to FAISS index
            doc_id = str(len(self.metadata))
            self.index.add(embedding.reshape(1, -1))
            
            # Store document mapping
            self.metadata[doc_id] = document
            
            # Save updated index
            self.save()
            
            return doc_id
        except Exception as e:
            logger.error(f"Error adding document to index: {str(e)}", exc_info=True)
            raise
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """Search the index for similar documents."""
        try:
            # Search FAISS index
            distances, indices = self.index.search(query_embedding.reshape(1, -1), k)
            
            # Get results with relevance filtering
            results = []
            for i, (idx, distance) in enumerate(zip(indices[0], distances[0])):
                if idx != -1:  # -1 indicates no result
                    doc = self.metadata[str(idx)]
                    
                    # Calculate score (lower distance = higher score)
                    # For L2 distance on normalized vectors, typical ranges:
                    # - 0-1: very similar
                    # - 1-2: somewhat similar  
                    # - 2+: dissimilar
                    # Use a more conservative threshold
                    score = float(np.exp(-distance / 3))  # More aggressive filtering
                    
                    # Only include results with a minimum relevance score
                    # Higher threshold = more relevant results only
                    min_score_threshold = 0.3  # Only include results with >30% relevance
                    
                    if score >= min_score_threshold:
                        result = {
                            'url': doc['url'],
                            'content': doc['content'],
                            'score': score
                        }
                        # Add title if it exists
                        if 'title' in doc:
                            result['title'] = doc['title']
                        results.append(result)
                    else:
                        # Log filtered out results for debugging
                        logger.debug(f"Filtered out low-relevance result: {doc.get('url', 'unknown')} (score: {score:.3f}, distance: {distance:.3f})")
            
            # Sort results by score in descending order (most relevant first)
            results.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"Search returned {len(results)} relevant results (filtered by score >= {min_score_threshold})")
            
            return results
        except Exception as e:
            logger.error(f"Error searching index: {str(e)}", exc_info=True)
            raise
    
    def size(self) -> int:
        """Get the number of documents in the index."""
        return len(self.metadata)
    
    def clear(self):
        """Clear the index."""
        try:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = {}
            self.save()
            logger.info("Index cleared")
        except Exception as e:
            logger.error(f"Error clearing index: {str(e)}", exc_info=True)
            raise

    def contains_url(self, url: str) -> bool:
        """Check if a URL is already indexed."""
        try:
            # Check if URL exists in metadata
            for doc in self.metadata.values():
                if doc.get('url') == url:
                    logger.info(f"URL already indexed: {url}")
                    return True
            logger.info(f"URL not found in index: {url}")
            return False
        except Exception as e:
            logger.error(f"Error checking URL in index: {str(e)}", exc_info=True)
            return False 
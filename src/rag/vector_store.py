import logging
from typing import List, Dict, Any, Optional
from uuid import uuid4
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from src.config import Config
from src.rag.embeddings import EmbeddingManager


"""Manages Qdrant vector stores for incidents and runbooks"""
class VectorStoreManager:

    def __init__(
        self,
        store_type: str = "incidents",
        embedding_model: str = "text-embedding-3-large",
        qdrant_url: str = "http://localhost:6333"
    ):
        if store_type not in ["incidents", "runbooks"]:
            raise ValueError(f"Invalid store_type: {store_type}. Must be 'incidents' or 'runbooks'")

        self.store_type = store_type
        self.collection_name = f"devops_{store_type}"  # e.g., "devops_incidents"

        # Initialize embedding manager
        self.embedding_manager = EmbeddingManager(model=embedding_model)

        # Get embedding dimension based on model
        self.embedding_dim = self._get_embedding_dimension(embedding_model)

        # Connect to Qdrant
        self.client = QdrantClient(url=qdrant_url)

        logging.debug(f"Connected to Qdrant at {qdrant_url}")

    # Embedding dimensions of Vector DB
    def _get_embedding_dimension(self, model: str) -> int:
        dimensions = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536,
        }
        return dimensions.get(model, 1536)

    def create_collection(self) -> None:
        # Check if collection already exists
        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]

        if self.collection_name in collection_names:
            logging.info(f"Collection '{self.collection_name}' already exists")
            return

        # Create collection with vector configuration
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE
            )
        )
        logging.info(f"Created collection: {self.collection_name}")

    def delete_collection(self) -> None:
        self.client.delete_collection(collection_name=self.collection_name)
        logging.debug(f"Deleted collection: {self.collection_name}")

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        if not documents:
            raise ValueError("Cannot add empty documents")

        # Ensure collection exists
        self.create_collection()

        # Extract texts and metadata
        texts = [doc.get("content", "") for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]

        embeddings = self.embedding_manager.embed_documents(texts)
        points = []
        for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
            point_id = str(uuid4())

            payload = {
                "content": text,
                **metadata
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            )

        # Upload to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        logging.info(f"Added {len(documents)} documents to '{self.collection_name}'")

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:

        query_vector = self.embedding_manager.embed_text(query)

        query_filter = None
        if filter_dict:
            conditions = []
            for key, value in filter_dict.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            query_filter = Filter(must=conditions)

        # Search in Qdrant
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=k,
            query_filter=query_filter
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "content": result.payload.get("content", ""),
                "metadata": {k: v for k, v in result.payload.items() if k != "content"},
                "score": result.score
            })

        return formatted_results

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        return self.similarity_search(query, k=k)

    def get_collection_info(self) -> Dict[str, Any]:

        info = self.client.get_collection(collection_name=self.collection_name)

        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
        }

    def collection_exists(self) -> bool:
        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]
        return self.collection_name in collection_names

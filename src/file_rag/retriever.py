"""Document retriever using file-based vector store"""

import logging
from typing import List, Dict, Any, Optional
from src.file_rag.embeddings import EmbeddingManager
from src.file_rag.vector_store import FileVectorStore


class DocumentRetriever:
    """Retrieves similar incidents and relevant runbooks using file-based vector search"""

    def __init__(self, data_dir: str = "data/vectors"):
        self.data_dir = data_dir
        self.embeddings = EmbeddingManager(model_name="text-embedding-3-large")
        self.vector_store = FileVectorStore(data_dir=data_dir)

        logging.info("File-based DocumentRetriever initialized")

    def search_incidents(
        self,
        query: str,
        k: int = 3,
        service_filter: Optional[str] = None,
        severity_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:

        logging.info(f"Searching incidents: query='{query[:50]}...', k={k}")

        # Create query embedding
        query_vector = self.embeddings.embed_query(query)

        # Build filters
        filters = {}
        if service_filter:
            filters['service'] = service_filter
        if severity_filter:
            filters['severity'] = severity_filter

        # Search
        results = self.vector_store.search(
            collection_name="devops_incidents",
            query_vector=query_vector,
            limit=k,
            filters=filters if filters else None
        )

        logging.info(f"Found {len(results)} similar incidents")
        return results

    def search_runbooks(
        self,
        query: str,
        k: int = 3,
        service_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:

        logging.info(f"Searching runbooks: query='{query[:50]}...', k={k}")

        # Create query embedding
        query_vector = self.embeddings.embed_query(query)

        # Build filters
        filters = {}
        if service_filter:
            filters['service'] = service_filter

        # Search
        results = self.vector_store.search(
            collection_name="devops_runbooks",
            query_vector=query_vector,
            limit=k,
            filters=filters if filters else None
        )

        logging.info(f"Found {len(results)} relevant runbooks")
        return results

    def get_status(self) -> Dict[str, Any]:

        incidents_info = self.vector_store.get_collection_info("devops_incidents")
        runbooks_info = self.vector_store.get_collection_info("devops_runbooks")

        return {
            "incidents": incidents_info,
            "runbooks": runbooks_info
        }

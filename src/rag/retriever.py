import logging
from typing import List, Dict, Any, Optional
from src.rag.vector_store import VectorStoreManager

class DocumentRetriever:

    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.qdrant_url = qdrant_url
        self.incident_store = VectorStoreManager(
            store_type="incidents",
            qdrant_url=qdrant_url
        )
        self.runbook_store = VectorStoreManager(
            store_type="runbooks",
            qdrant_url=qdrant_url
        )
        self._check_collections()

    def _check_collections(self) -> None:
        if self.incident_store.collection_exists():
            info = self.incident_store.get_collection_info()
            logging.info(f"Incident collection: {info['points_count']} documents")
        else:
            logging.info("Incident collection does not exist yet")

        if self.runbook_store.collection_exists():
            info = self.runbook_store.get_collection_info()
            logging.info(f"Runbook collection: {info['points_count']} documents")
        else:
            logging.info("Runbook collection does not exist yet")

    def search_incidents(
        self,
        query: str,
        k: int = 3,
        service_filter: Optional[str] = None,
        severity_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:

        if not self.incident_store.collection_exists():
            logging.info("Incident collection does not exist. No results to return.")
            return []

        # Build filter dictionary
        filter_dict = {}
        if service_filter:
            filter_dict["service"] = service_filter
        if severity_filter:
            filter_dict["severity"] = severity_filter

        # Search
        results = self.incident_store.similarity_search(
            query,
            k=k,
            filter_dict=filter_dict if filter_dict else None
        )

        return results

    def search_runbooks(
        self,
        query: str,
        k: int = 3,
        service_filter: Optional[str] = None,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:

        if not self.runbook_store.collection_exists():
            logging.debug("Runbook collection does not exist. No results to return.")
            return []

        filter_dict = {}
        if service_filter:
            filter_dict["service"] = service_filter
        if category_filter:
            filter_dict["category"] = category_filter

        results = self.runbook_store.similarity_search(
            query,
            k=k,
            filter_dict=filter_dict if filter_dict else None
        )

        return results

    def search_incidents_with_scores(
        self,
        query: str,
        k: int = 3
    ) -> List[Dict[str, Any]]:
        return self.search_incidents(query, k=k)

    def search_runbooks_with_scores(
        self,
        query: str,
        k: int = 3
    ) -> List[Dict[str, Any]]:
        return self.search_runbooks(query, k=k)

    def get_incident_store(self) -> VectorStoreManager:
        return self.incident_store

    def get_runbook_store(self) -> VectorStoreManager:
        return self.runbook_store

    def get_status(self) -> Dict[str, Any]:
        status = {
            "qdrant_url": self.qdrant_url,
            "incidents": {},
            "runbooks": {}
        }

        if self.incident_store.collection_exists():
            status["incidents"] = self.incident_store.get_collection_info()
        else:
            status["incidents"] = {"status": "not_created"}

        if self.runbook_store.collection_exists():
            status["runbooks"] = self.runbook_store.get_collection_info()
        else:
            status["runbooks"] = {"status": "not_created"}

        return status

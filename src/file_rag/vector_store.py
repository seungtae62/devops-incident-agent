"""File-based vector store (replaces Qdrant)"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
import logging


class FileVectorStore:
    """File-based vector store using JSON files and numpy for similarity search"""

    def __init__(self, data_dir: str = "data/vectors"):
        """
        Initialize file-based vector store

        Args:
            data_dir: Directory containing vector JSON files
        """
        self.data_dir = Path(data_dir)
        self.incidents_data = []
        self.runbooks_data = []
        self._load_data()

    def _load_data(self):
        """Load vector data from JSON files"""
        incidents_file = self.data_dir / "incidents.json"
        runbooks_file = self.data_dir / "runbooks.json"

        if incidents_file.exists():
            with open(incidents_file, 'r') as f:
                self.incidents_data = json.load(f)
            logging.info(f"Loaded {len(self.incidents_data)} incidents from {incidents_file}")
        else:
            logging.warning(f"Incidents file not found: {incidents_file}")

        if runbooks_file.exists():
            with open(runbooks_file, 'r') as f:
                self.runbooks_data = json.load(f)
            logging.info(f"Loaded {len(self.runbooks_data)} runbooks from {runbooks_file}")
        else:
            logging.warning(f"Runbooks file not found: {runbooks_file}")

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors

        Args:
            collection_name: Name of collection (incidents or runbooks)
            query_vector: Query embedding vector
            limit: Number of results to return
            filters: Metadata filters (e.g., {"service": "Database"})

        Returns:
            List of results with metadata and scores
        """
        # Select data source
        if "incident" in collection_name.lower():
            data = self.incidents_data
        elif "runbook" in collection_name.lower():
            data = self.runbooks_data
        else:
            logging.error(f"Unknown collection: {collection_name}")
            return []

        if not data:
            logging.warning(f"No data available for {collection_name}")
            return []

        # Apply filters
        filtered_data = self._apply_filters(data, filters)

        if not filtered_data:
            logging.info(f"No results after filtering, using all {len(data)} items")
            filtered_data = data

        # Compute similarities
        embeddings_matrix = np.array([item['embedding'] for item in filtered_data])
        query_vector_array = np.array([query_vector])

        similarities = cosine_similarity(query_vector_array, embeddings_matrix)[0]

        # Get top k results
        top_indices = np.argsort(similarities)[::-1][:limit]

        results = []
        for idx in top_indices:
            item = filtered_data[idx]
            results.append({
                'id': item.get('id'),
                'score': float(similarities[idx]),
                'payload': item.get('metadata', {}),
                'metadata': item.get('metadata', {}),
                'text': item.get('text', '')
            })

        return results

    def _apply_filters(
        self,
        data: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply metadata filters to data"""
        if not filters:
            return data

        filtered = []
        for item in data:
            metadata = item.get('metadata', {})
            match = True

            for key, value in filters.items():
                if key not in metadata or metadata[key] != value:
                    match = False
                    break

            if match:
                filtered.append(item)

        return filtered

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a collection"""
        if "incident" in collection_name.lower():
            count = len(self.incidents_data)
        elif "runbook" in collection_name.lower():
            count = len(self.runbooks_data)
        else:
            count = 0

        return {
            "points_count": count,
            "status": "ok" if count > 0 else "empty"
        }

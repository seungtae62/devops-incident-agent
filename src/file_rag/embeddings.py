"""Embedding management for file-based RAG (same as original)"""

from langchain_openai import AzureOpenAIEmbeddings
from src.config import Config


class EmbeddingManager:
    """Manages embedding models for vector search"""

    def __init__(self, model_name: str = "text-embedding-3-large"):
        self.model_name = model_name
        self.embeddings = self._create_embeddings()

    def _create_embeddings(self) -> AzureOpenAIEmbeddings:
        """Create AzureOpenAI embeddings instance"""

        # Map model names to deployment names
        model_mapping = {
            "text-embedding-3-large": Config.AI_DEPLOY_EMBED_3_LARGE,
            "text-embedding-3-small": Config.AI_DEPLOY_EMBED_3_SMALL,
            "text-embedding-ada-002": Config.AI_DEPLOY_EMBED_ADA
        }

        deployment_name = model_mapping.get(self.model_name, Config.AI_DEPLOY_EMBED_3_LARGE)

        return AzureOpenAIEmbeddings(
            azure_endpoint=Config.AI_ENDPOINT,
            api_key=Config.AI_API_KEY,
            azure_deployment=deployment_name,
            api_version="2024-02-01"
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of documents"""
        return self.embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query"""
        return self.embeddings.embed_query(text)

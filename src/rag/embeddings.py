import logging
from typing import List
from langchain_openai import AzureOpenAIEmbeddings
from src.config import Config


class EmbeddingManager:

    def __init__(self, model: str = "text-embedding-3-large"):
        self.model = model
        self.embeddings = self._create_embeddings()

    def _create_embeddings(self) -> AzureOpenAIEmbeddings:
        deployment_map = {
            "text-embedding-3-large": Config.AI_DEPLOY_EMBED_3_LARGE,
            "text-embedding-3-small": Config.AI_DEPLOY_EMBED_3_SMALL,
            "text-embedding-ada-002": Config.AI_DEPLOY_EMBED_ADA,
        }

        deployment_name = deployment_map.get(self.model)
        if not deployment_name:
            raise ValueError(f"Unsupported embedding model: {self.model}")

        return AzureOpenAIEmbeddings(
            azure_endpoint=Config.AI_ENDPOINT,
            api_key=Config.AI_API_KEY,
            azure_deployment=deployment_name,
            api_version="2024-02-01"
        )

    def embed_text(self, text: str) -> List[float]:
        return self.embeddings.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)

    def get_langchain_embeddings(self) -> AzureOpenAIEmbeddings:
        return self.embeddings

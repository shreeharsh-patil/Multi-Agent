from abc import ABC, abstractmethod
from typing import Optional


class VectorStore(ABC):
    @abstractmethod
    async def store_embeddings(
        self,
        collection: str,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
    ) -> None:
        pass

    @abstractmethod
    async def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter: Optional[dict] = None,
    ) -> list[dict]:
        pass

    @abstractmethod
    async def delete(
        self,
        collection: str,
        ids: list[str],
    ) -> None:
        pass

    @abstractmethod
    async def create_collection(self, collection: str) -> None:
        pass

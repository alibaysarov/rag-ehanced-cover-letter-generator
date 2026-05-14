import logging

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, PointIdsList
from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantStorage():
    def __init__(
        self,
        url=settings.QDRANT_URL,
        collection_name: str = "cvs",
        dim: int = 768,
        recreate_on_dim_mismatch: bool = False,
    ):
        print("qdrant init")
        self.client = QdrantClient(url=url)
        self.collection = collection_name
        self._ensure_collection(dim=dim, recreate_on_dim_mismatch=recreate_on_dim_mismatch)

    def _ensure_collection(self, dim: int, recreate_on_dim_mismatch: bool):
        if not self.client.collection_exists(collection_name=self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            return

        info = self.client.get_collection(collection_name=self.collection)
        existing_dim = info.config.params.vectors.size
        if existing_dim == dim:
            return

        if not recreate_on_dim_mismatch:
            raise RuntimeError(
                f"Qdrant collection '{self.collection}' has dim={existing_dim}, "
                f"but embedder requires dim={dim}. "
                f"Recreate it manually or pass recreate_on_dim_mismatch=True."
            )

        logger.warning(
            "Qdrant collection '%s' has dim=%d, recreating with dim=%d (data lost)",
            self.collection, existing_dim, dim,
        )
        self.client.delete_collection(collection_name=self.collection)
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    def upsert(self,ids,vectors,payloads):
        points = [PointStruct(id=ids[i],vector=vectors[i],payload=payloads[i]) for i in range(len(ids))]
        self.client.upsert(collection_name=self.collection,points=points)


    def search(self, query_vector, top_k: int = 5, query_filter: Filter | None = None):
        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            with_payload=True,
            limit=top_k,
            query_filter=query_filter,
        ).points

        contexts = []
        sources = []
        scores = []

        for r in results:
            payload = getattr(r,"payload",None) or {}
            text = payload.get("text","")
            if text:
                contexts.append(text)
                sources.append(payload)
                scores.append(getattr(r, "score", None))
        return {"contexts":contexts, "sources":sources, "scores": scores}
    
    def delete_by_source_id(self, source_id: int):
        """Delete all points with given source_id"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source_id",
                        match=MatchValue(value=source_id)
                    )
                ]
            )
        )

    def get_points_by_source_id(self, source_id: int):
        """Get all points for potential rollback"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        results = self.client.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="source_id",
                        match=MatchValue(value=source_id)
                    )
                ]
            ),
            limit=10000,
            with_payload=True,
            with_vectors=True
        )
        return results[0]

    def list_by_user_id(self, user_id: int) -> list[dict]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        points, _ = self.client.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id),
                    )
                ]
            ),
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )
        return [{"id": str(p.id), "payload": p.payload or {}} for p in points]

    def get_point_by_id(self, point_id: str) -> dict | None:
        results = self.client.retrieve(
            collection_name=self.collection,
            ids=[point_id],
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            return None
        point = results[0]
        return {"id": str(point.id), "payload": point.payload or {}}

    def delete_by_point_id(self, point_id: str):
        self.client.delete(
            collection_name=self.collection,
            points_selector=PointIdsList(points=[point_id]),
        )


_vector_storage = None

def get_vector_storage() -> QdrantStorage:
    global _vector_storage
    if _vector_storage is None:
        _vector_storage = QdrantStorage()
    return _vector_storage


_projects_storage_by_dim: dict[int, "QdrantStorage"] = {}

def get_projects_storage(dim: int = 768) -> QdrantStorage:
    if dim not in _projects_storage_by_dim:
        _projects_storage_by_dim[dim] = QdrantStorage(
            collection_name="projects",
            dim=dim,
            recreate_on_dim_mismatch=True,
        )
    return _projects_storage_by_dim[dim]

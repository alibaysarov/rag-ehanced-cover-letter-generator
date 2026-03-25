from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance,PointStruct
from app.core.config import settings


class QdrantStorage():
    def __init__(self,url=settings.QDRANT_URL, collection_name:str = "cvs",dim=3072):
        print("qdrant init")
        self.client = QdrantClient(url=url)
        self.collection = collection_name
        if not self.client.collection_exists(collection_name=collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
    def upsert(self,ids,vectors,payloads):
        points = [PointStruct(id=ids[i],vector=vectors[i],payload=payloads[i]) for i in range(len(ids))]
        self.client.upsert(collection_name=self.collection,points=points)
    def search(self,query_vector,top_k:int=5):
        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            with_payload=True,
            limit=top_k
        ).points

        contexts = []
        sources = []

        for r in results:
            payload = getattr(r,"payload",None) or {}
            text = payload.get("text","")
            if text:
                contexts.append(text)
                sources.append(payload)
        return {"contexts":contexts, "sources":sources}
    
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


_vector_storage = None

def get_vector_storage() -> QdrantStorage:
    global _vector_storage
    if _vector_storage is None:
        _vector_storage = QdrantStorage()
    return _vector_storage

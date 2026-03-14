import uuid

from injector import inject
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from services.vectorisation.VectorizerGemini import VectorizerGemini
from services.vectorisation.vectorizer_gemini.task_types import RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY

COLLECTION_NAME = "memories"
VECTOR_SIZE = 768


class MemoriesRepository:

    @inject
    def __init__(self, qdrant_client: QdrantClient, vectorizer: VectorizerGemini):
        self.qdrant_client = qdrant_client
        self.vectorizer = vectorizer
        self._ensure_collection()

    def _ensure_collection(self):
        collections = [c.name for c in self.qdrant_client.get_collections().collections]
        if COLLECTION_NAME not in collections:
            self.qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )

    def save(self, user_id: str, text: str, metadata: dict = None) -> str:
        """Save a memory and return its id."""
        vector = self.vectorizer.vectorize_one(text, task_type=RETRIEVAL_DOCUMENT)
        point_id = str(uuid.uuid4())
        payload = {"user_id": user_id, "text": text}
        if metadata:
            payload["metadata"] = metadata

        self.qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return point_id

    def search(self, user_id: str, query: str, limit: int = 5) -> list[dict]:
        """Search memories for a user by semantic similarity."""
        vector = self.vectorizer.vectorize_one(query, task_type=RETRIEVAL_QUERY)

        results = self.qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            query_filter=Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]),
            limit=limit,
        )

        return [
            {"id": point.id, "text": point.payload["text"], "score": point.score,
             "metadata": point.payload.get("metadata")}
            for point in results.points
        ]

    def get_by_id(self, point_id: str) -> dict | None:
        """Retrieve a single memory by its id."""
        results = self.qdrant_client.retrieve(collection_name=COLLECTION_NAME, ids=[point_id])
        if not results:
            return None
        point = results[0]
        return {"id": point.id, "text": point.payload["text"], "metadata": point.payload.get("metadata")}

    def delete(self, point_id: str):
        """Delete a memory by its id."""
        self.qdrant_client.delete(collection_name=COLLECTION_NAME, points_selector=[point_id])

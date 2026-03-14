from google import genai
from google.genai import types
from injector import inject

from services.vectorisation.vectorizer_gemini.task_types import SEMANTIC_SIMILARITY


class VectorizerGemini:
    """Vectorizer using Google Gemini Embedding model. See # Google Gemini embedding size. See https://ai.google.dev/gemini-api/docs/embeddings"""

    @inject
    def __init__(self, output_dimensionality: int = 768, model: str = "gemini-embedding-001"):
        self.genai_client = genai.Client()
        self.output_dimensionality = output_dimensionality
        self.model = model

    def vectorize_one(self, text: str, task_type=SEMANTIC_SIMILARITY) -> list[float]:
        response = self.genai_client.models.embed_content(
            model=self.model,
            contents=[text], config=types.EmbedContentConfig(output_dimensionality=self.output_dimensionality, task_type=task_type)
        )

        return list(response.embeddings[0].values)

    def vectorize_batch(self, texts: list[str], task_type=SEMANTIC_SIMILARITY) -> list[list[float]]:
        response = self.genai_client.models.embed_content(
            model=self.model,
            contents=texts, config=types.EmbedContentConfig(output_dimensionality=self.output_dimensionality, task_type=task_type)
        )

        return [list(embedding.values) for embedding in response.embeddings]

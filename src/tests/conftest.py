import math

import pytest
from injector import Injector, Module, singleton
from qdrant_client import QdrantClient
from unittest.mock import MagicMock

from services.vectorisation.VectorizerGemini import VectorizerGemini


def _make_fake_vector(seed: float = 0.1) -> list[float]:
    """Create a deterministic 768-dim vector for testing without hitting Gemini API."""
    return [math.sin(seed * (i + 1)) for i in range(768)]


def _build_vectorizer_mock() -> MagicMock:
    mock = MagicMock(spec=VectorizerGemini)
    call_counter = {"n": 0}

    def side_effect(text, task_type=None):
        call_counter["n"] += 1
        return _make_fake_vector(seed=call_counter["n"] * 0.1 + hash(text) % 100)

    mock.vectorize_one.side_effect = side_effect
    return mock


class TestPatronModule(Module):
    """PatronModule fork for tests: in-memory Qdrant, mocked vectorizer."""

    def configure(self, binder) -> None:
        binder.bind(QdrantClient, to=QdrantClient(location=":memory:"), scope=singleton)
        binder.bind(VectorizerGemini, to=_build_vectorizer_mock(), scope=singleton)


@pytest.fixture()
def test_container():
    """Injector wired with TestPatronModule (in-memory Qdrant, mocked vectorizer)."""
    return Injector([TestPatronModule()])

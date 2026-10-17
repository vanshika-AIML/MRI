"""Embedding repository — CRUD + vector similarity search via pgvector."""
from __future__ import annotations

import uuid
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.embedding import Embedding


class EmbeddingRepository:
    """Data-access methods for the ``embeddings`` table.

    The ``similarity_search`` method leverages pgvector's
    ``<->`` (L2 / Euclidean) distance operator to find the closest
    embeddings to a query vector.  The distance metric can be changed
    once the embedding workload characteristics are known.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────
    def create(
        self,
        *,
        study_id: uuid.UUID,
        embedding_type: str,
        model_name: str,
        embedding: list[float],
        **kwargs,
    ) -> Embedding:
        emb = Embedding(
            study_id=study_id,
            embedding_type=embedding_type,
            model_name=model_name,
            embedding=embedding,
            **kwargs,
        )
        self.db.add(emb)
        self.db.flush()
        return emb

    # ── Read ──────────────────────────────────────────────────────
    def get_by_id(self, embedding_id: uuid.UUID) -> Optional[Embedding]:
        return self.db.get(Embedding, embedding_id)

    def list_by_study(
        self, study_id: uuid.UUID, *, offset: int = 0, limit: int = 100,
    ) -> List[Embedding]:
        stmt = (
            select(Embedding)
            .where(Embedding.study_id == study_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    # ── Vector similarity search ──────────────────────────────────
    def similarity_search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 10,
        embedding_type: str | None = None,
    ) -> Sequence[Tuple[Embedding, float]]:
        """Find the nearest embeddings to *query_embedding*.

        Returns a list of ``(Embedding, distance)`` tuples ordered
        by ascending L2 distance.

        Args:
            query_embedding: The query vector (must match the stored
                dimension).
            limit: Maximum number of results.
            embedding_type: Optional filter to restrict by
                ``embedding_type``.
        """
        distance = Embedding.embedding.l2_distance(query_embedding)
        stmt = select(Embedding, distance.label("distance"))

        if embedding_type is not None:
            stmt = stmt.where(Embedding.embedding_type == embedding_type)

        stmt = stmt.order_by(distance).limit(limit)

        rows = self.db.execute(stmt).all()
        return [(row[0], row[1]) for row in rows]

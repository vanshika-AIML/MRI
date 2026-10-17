"""Image repository — CRUD operations for Image entities."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.image import Image


class ImageRepository:
    """Data-access methods for the ``images`` table."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Create ────────────────────────────────────────────────────
    def create(
        self,
        *,
        series_id: uuid.UUID,
        sop_instance_uid: str,
        file_path: str,
        **kwargs,
    ) -> Image:
        image = Image(
            series_id=series_id,
            sop_instance_uid=sop_instance_uid,
            file_path=file_path,
            **kwargs,
        )
        self.db.add(image)
        self.db.flush()
        return image

    # ── Read ──────────────────────────────────────────────────────
    def get_by_id(self, image_id: uuid.UUID) -> Optional[Image]:
        return self.db.get(Image, image_id)

    def list_by_series(
        self, series_id: uuid.UUID, *, offset: int = 0, limit: int = 100,
    ) -> List[Image]:
        stmt = (
            select(Image)
            .where(Image.series_id == series_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

"""Series repository for database access."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.series import Series


class SeriesRepository:
    """CRUD operations for the Series entity."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        study_id: UUID,
        series_instance_uid: str,
        series_number: int = 1,
        series_description: Optional[str] = None,
        **kwargs,
    ) -> Series:
        series = Series(
            study_id=study_id,
            series_uid=series_instance_uid,
            series_number=series_number,
            description=series_description,
        )
        self.db.add(series)
        self.db.flush()
        return series

    def get_by_id(self, series_id: UUID) -> Optional[Series]:
        return self.db.get(Series, series_id)

    def get_by_series_uid(self, series_uid: str) -> Optional[Series]:
        stmt = select(Series).where(Series.series_uid == series_uid)
        return self.db.execute(stmt).scalars().first()

    def list_by_study(self, study_id: UUID) -> List[Series]:
        stmt = select(Series).where(Series.study_id == study_id)
        return list(self.db.execute(stmt).scalars().all())

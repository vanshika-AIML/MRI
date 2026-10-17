"""Database domain models (PostgreSQL / SQLAlchemy / pgvector).

Importing this module ensures all models are registered with the
declarative Base.metadata so Alembic autogenerate can discover them.
"""
from app.models.patient import Patient
from app.models.study import Study
from app.models.series import Series
from app.models.image import Image
from app.models.analysis import Analysis
from app.models.embedding import Embedding
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.annotation import AnalysisAnnotation
from app.models.report import AnalysisReport

__all__ = [
    "Patient",
    "Study",
    "Series",
    "Image",
    "Analysis",
    "Embedding",
    "User",
    "AuditLog",
    "AnalysisAnnotation",
]

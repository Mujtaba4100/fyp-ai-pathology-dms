from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.database_models import Base, Document, PathologyReport, User

def _normalize_database_url(url: str) -> str:
    """Normalize common Postgres URL variants for SQLAlchemy."""
    url = (url or "").strip()
    # Heroku/Neon-style URLs sometimes use postgres:// which SQLAlchemy doesn't accept.
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _build_database_url() -> str:
    """Select DB target.

    Rules:
    - If DATABASE_URL is set -> use it (Neon / cloud Postgres).
    - Else -> build from POSTGRES_* (local fallback).
    """
    if getattr(settings, "DATABASE_URL", ""):
        return _normalize_database_url(settings.DATABASE_URL)

    return (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


# Create database URL
DATABASE_URL = _build_database_url()

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    try:
        # Required for pgvector columns (DocumentEmbedding.embedding).
        # On managed Postgres (e.g., Neon), this typically works, but some roles may not
        # have privileges. If extension creation fails, we still create the core tables
        # needed for Phase 1–6 persistence (documents + pathology_reports + users).
        vector_enabled = False
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            vector_enabled = True
        except Exception as ext_err:
            print(
                "⚠️  pgvector extension could not be enabled. "
                "Skipping vector tables (document_embeddings). "
                f"Reason: {ext_err}"
            )

        if vector_enabled:
            Base.metadata.create_all(bind=engine)
        else:
            Base.metadata.create_all(
                bind=engine,
                tables=[Document.__table__, PathologyReport.__table__, User.__table__],
            )
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

# Create tables on startup/import
init_db()

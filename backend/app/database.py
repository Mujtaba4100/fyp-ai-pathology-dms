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


def _auto_migrate_vector_dimension():
    """
    Auto-migration: upgrade the embedding column from vector(384) → vector(768).

    This runs every startup but is a no-op if the column is already 768-dim or
    if the table does not yet exist. No manual migration script needed.
    """
    TARGET_DIM = 768
    try:
        with engine.connect() as conn:
            # 1. Check table exists
            table_exists = conn.execute(
                text(
                    "SELECT EXISTS ("
                    "  SELECT FROM information_schema.tables "
                    "  WHERE table_name = 'document_embeddings'"
                    ")"
                )
            ).scalar()
            if not table_exists:
                return  # Table will be created fresh with correct dim by create_all()

            # 2. Read current dimension from pg_attribute
            row = conn.execute(
                text(
                    "SELECT atttypmod FROM pg_attribute "
                    "JOIN pg_class ON pg_class.oid = pg_attribute.attrelid "
                    "WHERE pg_class.relname = 'document_embeddings' "
                    "  AND pg_attribute.attname = 'embedding'"
                )
            ).fetchone()

            if row is None:
                return  # No embedding column yet

            current_dim = row[0]  # atttypmod stores the dimension for vector type
            if current_dim == TARGET_DIM:
                return  # Already correct — nothing to do

            # 3. Dimension mismatch — resize column (drop + recreate, pgvector limitation)
            print(
                f"[INFO] Auto-migrating embedding column: {current_dim}-dim → {TARGET_DIM}-dim "
                f"(BioLORD-2023-M upgrade). Existing vectors cleared."
            )
            conn.execute(
                text("ALTER TABLE document_embeddings DROP COLUMN IF EXISTS embedding")
            )
            conn.execute(
                text(f"ALTER TABLE document_embeddings ADD COLUMN embedding vector({TARGET_DIM})")
            )
            conn.commit()
            print(f"[INFO] Embedding column upgraded to vector({TARGET_DIM}) ✓")

    except Exception as e:
        # Non-fatal — log and continue. The app still works; embeddings just won't save.
        print(f"[WARN] Vector dimension auto-migration failed (non-fatal): {e}")


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
                "[WARN] pgvector extension could not be enabled. "
                "Skipping vector tables (document_embeddings). "
                f"Reason: {ext_err}"
            )

        if vector_enabled:
            Base.metadata.create_all(bind=engine)
            # Auto-migrate vector dimension for BioLORD-2023-M (384 → 768)
            _auto_migrate_vector_dimension()
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

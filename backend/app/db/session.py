from sqlmodel import create_engine, Session
from pathlib import Path
import os, sys

# Database path strategy:
# 1) Packaged (onefile/onedir): Prioritize same directory as executable
# 2) Development: In source backend directory
# 3) Support overriding absolute path via environment variable AIAUTHOR_DB_PATH
if getattr(sys, "frozen", False):
	base_dir = Path(sys.executable).resolve().parent
else:
	base_dir = Path(__file__).resolve().parents[2]

DB_FILE = Path(os.getenv("AIAUTHOR_DB_PATH", (base_dir / 'aiauthor.db').as_posix()))
DATABASE_URL = f"sqlite:///{DB_FILE.as_posix()}"

# Create database engine (SQLite needs this argument to allow multi-thread access)
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})


def get_session():
    """
    FastAPI dependency that provides a transactional database session.
    It ensures that the session is committed on success and rolled back on error.
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close() 
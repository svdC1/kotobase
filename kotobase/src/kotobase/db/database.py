from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Get the directory of the current file
file_dir = Path(__file__).resolve().parent

# Construct the path to the database file
DATABASE_URL = f"sqlite:///{file_dir / 'kotobase.db'}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """
    Provides a transactional scope around a series of database operations.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

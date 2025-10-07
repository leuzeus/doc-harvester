"""Database models and session utilities."""

# Standard library imports
from pathlib import Path
from typing import Generator

# Third-party imports
from sqlmodel import Field, Session, SQLModel, create_engine


# --------------------------------------------------------------------------------------
# Database configuration
# --------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "data.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


# --------------------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------------------
class Source(SQLModel, table=True):
    """Source configuration stored in the admin database."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    kind: str
    url: str | None = None
    enabled: bool = True
    extra: str | None = Field(default=None, description="Arbitrary YAML or JSON blob")


# --------------------------------------------------------------------------------------
# Session helpers
# --------------------------------------------------------------------------------------
def init_db() -> None:
    """Create database tables if they do not already exist."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session for request-scoped usage."""

    with Session(engine) as session:
        yield session


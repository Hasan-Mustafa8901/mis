from sqlmodel import create_engine, Session
from dotenv import load_dotenv
import os

# Load environment variables from .env if present
load_dotenv()

# Use DATABASE_URL if set (for Postgres), else fallback to SQLite for development
database_url = os.getenv("DATABASE_URL")
if database_url:
    engine = create_engine(database_url, echo=False)
else:
    engine = create_engine("sqlite:///mis_db.db", echo=False)


def get_session():
    with Session(engine) as session:
        yield session

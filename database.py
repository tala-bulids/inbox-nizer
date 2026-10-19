import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    hide_parameters=True,
    pool_size=5,
    max_overflow=5,
    pool_timeout=5,
    pool_recycle=1800,
    connect_args={
        'connect_timeout': 5,
        'options': '-c statement_timeout=30000 -c lock_timeout=5000',
    },
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

from fastapi import Depends
from authentication import current_user


def get_db(principal=Depends(current_user)):
    from ownership import OwnedSession
    db = OwnedSession(bind=engine, user_id=principal.id, autoflush=False)

    try:
        yield db
    finally:
        db.close()
        
class Base(DeclarativeBase):
    pass

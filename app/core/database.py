# Database Core Intialization (engine, Session).
import os
from dotenv import load_dotenv
from typing import Annotated
from sqlmodel import create_engine, Session
from fastapi import Depends

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")
engine = create_engine(DATABASE_URL)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

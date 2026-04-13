# Database Core Intialization (engine, Session).
import os
from dotenv import load_dotenv
from typing import Annotated
from sqlmodel import create_engine, Session
from fastapi import Depends

load_dotenv()

databaseUrl = os.getenv("DATABASE_URL", "dummy.postgrossomodo")
engine = create_engine(databaseUrl)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

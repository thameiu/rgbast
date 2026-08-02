# Database Core Intialization (engine, Session).
import logging
import os
from dotenv import load_dotenv
from typing import Annotated
from sqlmodel import create_engine, Session
from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()
logger = logging.getLogger("rgbast.database")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")

# Prod symptom: idle Postgres connections can be dropped by the provider/load balancer.
# `pool_pre_ping` validates a pooled connection before use and reconnects if needed.
# `pool_recycle` avoids keeping connections around longer than typical idle timeouts.
POOL_RECYCLE_SECONDS = int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800"))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=POOL_RECYCLE_SECONDS,
)


def get_session():
    with Session(engine) as session:
        try:
            yield session
        except SQLAlchemyError:
            logger.exception("database session failed during request")
            raise
        except Exception:
            raise
        finally:
            try:
                if session.in_transaction():
                    session.rollback()
            except SQLAlchemyError:
                logger.exception("database rollback failed after request error")


SessionDep = Annotated[Session, Depends(get_session)]

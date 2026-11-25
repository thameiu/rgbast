from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from app.core.database import SessionDep
from app.services.auth import AuthService
import jwt

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def optional_user(session: SessionDep, token_obj=Depends(optional_security)):
    return verify_token(session, token_obj) if token_obj else None


# Not really a middleware but useful for protecting certain routes only.
def verify_token(session: SessionDep, token_obj=Depends(security)):
    token = token_obj.credentials
    try:
        user = AuthService.check_auth(token, session)

    except jwt.exceptions.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Signature verification failed")

    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")

    except jwt.exceptions.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token format")

    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user

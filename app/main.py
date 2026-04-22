from fastapi import FastAPI
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from app.api import palettes, users, auth
from app.scripts.init_db import create_db_and_tables

app = FastAPI(title="RGBAST API")

ALLOWED_ORIGINS = [
    "https://rgbast-app.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

create_db_and_tables()

bearer_scheme = HTTPBearer()
# si le savoir est une arme, alors le savoir est une arme
app.include_router(users.router, tags=["users"])
app.include_router(auth.router, tags=["auth"])
app.include_router(palettes.router, tags=["palettes"])


@app.get("/")
async def root():
    return {"message": "Welcome to RGBAST ! If cou can read this, you can read this."}

import os
from datetime import datetime
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from sqlmodel import select

from app.api import palettes, users, auth, color, folders, search, colleagues
from app.core.database import SessionDep
from app.models.palette import Palette
from app.models.user import User
from app.services.palette import PaletteService

app = FastAPI(title="RGBAST API")

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://rgbast.com").rstrip("/")
SITEMAP_MAX_URLS = int(os.getenv("SITEMAP_MAX_URLS", "50000"))

ALLOWED_ORIGINS = [
    "https://rgbast-app.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer_scheme = HTTPBearer()
# si le savoir est une arme, alors le savoir est une arme
app.include_router(users.router, tags=["users"])
app.include_router(auth.router, tags=["auth"])
app.include_router(palettes.router, tags=["palettes"])
app.include_router(folders.router, tags=["folders"])
app.include_router(color.router, tags=["color"])
app.include_router(search.router, tags=["search"])
app.include_router(colleagues.router, tags=["colleagues"])


@app.get("/")
async def root():
    return {"message": "Welcome to RGBAST ! If cou can read this, you can read this, like really read this, like for real."}


def _build_absolute_url(path: str) -> str:
    return f"{FRONTEND_URL}{path}"


def _iso_lastmod(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _build_palette_path(username: str, folder_path: list[str], palette_title: str) -> str:
    encoded_username = quote(username, safe="")
    encoded_segments = [quote(segment, safe="") for segment in folder_path + [palette_title]]
    return f"/users/{encoded_username}/" + "/".join(encoded_segments)


def _resolve_sitemap_rows(session: SessionDep) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    static_entries = [
        {"loc": _build_absolute_url("/"), "changefreq": "daily", "priority": "1.0"},
        {"loc": _build_absolute_url("/search"), "changefreq": "daily", "priority": "0.8"},
        {"loc": _build_absolute_url("/color/B410CC"), "changefreq": "weekly", "priority": "0.7"},
        {"loc": _build_absolute_url("/register"), "changefreq": "monthly", "priority": "0.5"},
        {"loc": _build_absolute_url("/login"), "changefreq": "monthly", "priority": "0.5"},
    ]
    rows.extend(static_entries)

    users_list = session.exec(select(User).order_by(User.created_at.desc(), User.id.desc())).all()
    for user in users_list:
        rows.append(
            {
                "loc": _build_absolute_url(f"/users/{quote(user.username, safe='')}"),
                "changefreq": "weekly",
                "priority": "0.7",
                "lastmod": _iso_lastmod(user.created_at) or "",
            }
        )

    palettes_list = session.exec(
        select(Palette).order_by(Palette.created_at.desc(), Palette.id.desc())
    ).all()

    users_by_id = {user.id: user for user in users_list}
    for palette in palettes_list:
        owner = users_by_id.get(palette.user_id)
        if owner is None:
            continue

        folder_path = PaletteService._get_folder_path(palette.folder_id, session)
        latest_snapshot, _ = PaletteService.get_latest_palette_snapshot(
            palette.id, session, branch_id=None
        )
        lastmod = _iso_lastmod(latest_snapshot.created_at if latest_snapshot else palette.created_at) or ""
        rows.append(
            {
                "loc": _build_absolute_url(
                    _build_palette_path(owner.username, folder_path, palette.title)
                ),
                "changefreq": "weekly",
                "priority": "0.8",
                "lastmod": lastmod,
            }
        )

    return rows[:SITEMAP_MAX_URLS]


@app.get("/sitemap.xml")
def sitemap_xml(session: SessionDep) -> Response:
    rows = _resolve_sitemap_rows(session)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for row in rows:
        lines.append("  <url>")
        lines.append(f"    <loc>{row['loc']}</loc>")
        if row.get("lastmod"):
            lines.append(f"    <lastmod>{row['lastmod']}</lastmod>")
        if row.get("changefreq"):
            lines.append(f"    <changefreq>{row['changefreq']}</changefreq>")
        if row.get("priority"):
            lines.append(f"    <priority>{row['priority']}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return Response("\n".join(lines), media_type="application/xml")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt(request: Request) -> str:
    sitemap_url = str(request.url_for("sitemap_xml"))
    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /dashboard",
            "Disallow: /settings",
            "Disallow: /auth/complete",
            "Disallow: /reset-password",
            "Disallow: /forgot-password",
            "",
            f"Sitemap: {sitemap_url}",
        ]
    )

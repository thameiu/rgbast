# RGBAST API

Backend of [RGBAST](https://rgbast.com), a color palette editor that keeps the full history of every palette: each save is a snapshot, you can branch, merge and go back to any version.

Built with FastAPI, SQLModel and PostgreSQL. The frontend lives in [rgbast-web](https://github.com/thameiu/rgbast-web).

Production API: https://api.rgbast.com

## Features

### Accounts
- Registration and login with a username or an email address
- JWT authentication (HS256, tokens valid for 60 days), passwords hashed with Argon2
- Email verification, by link or by code, with resend
- Password reset by email
- Profile color: a random hex color is given at registration and can be changed later
- Account deletion

### Palettes and history
- A palette holds up to 15 colors, each with a hex value and an optional label
- Every save creates a snapshot. Only what changed is stored: each snapshot records the added, deleted and modified colors compared to its parent
- Colors are ordered with lexicographic position keys, so inserting or moving a color does not rewrite the others
- Branches: start a branch from any snapshot, keep working on it, then merge it back into main
- Revert main or a branch to an earlier snapshot
- History graph with added, deleted and modified counts per snapshot

### Folders
- Nested folders for palettes
- Palettes have readable URLs built from their folder path: `/users/<username>/<folder>/<subfolder>/<palette>`

### Colors
- Conversions to RGB, HSL, HSB, HWB, CMYK, LAB, LCH, LUV and XYZ
- Shades, tints, complementary, triadic and analogous colors, closest web safe color
- Closest color name (pycolornames)
- WCAG contrast ratio between two colors, and against white and black
- Color blindness simulation: protanopia, deuteranopia, tritanopia, achromatopsia
- Accessibility audit of a whole palette
- Bast index ☥: how hard a color is to name, from 0 to 100. It is the normalized entropy of the naming votes a color would get, computed in OKLab against 13 reference colors taken from the XKCD Color Survey. Exposed as `bast_score`

### Generation and extraction
- Palette generation from a harmony (analogous, complementary, triadic, split complementary, tetradic), a contrast level from 1 to 10, optional shades and up to 5 base colors
- Dominant color extraction from an image (1 to 15 colors, 50 MB max). Raster images are quantized with Pillow; SVG files are parsed for their fill, stroke and stop colors

### Social
- Color bookmarks, with a custom label
- Colleagues: send, accept and remove requests
- Search users, and search palettes by name or by color
- Discover: recent palettes and palettes from your colleagues

### Other
- `sitemap.xml`, a paginated sitemap of every hex color page, and `robots.txt`
- `GET /health/db` for health checks

Interactive documentation is available on `/docs` once the API is running.

## Stack

| | |
|---|---|
| Language | Python 3.14, managed with [uv](https://docs.astral.sh/uv/) |
| Framework | FastAPI, Uvicorn |
| Database | PostgreSQL 16, SQLModel, SQLAlchemy |
| Migrations | Alembic |
| Images | Pillow |
| Lint | Ruff |

## Project layout

```
app/
  api/           routes
  controllers/   responses and error handling
  core/          database engine and session
  middlewares/   authentication
  models/        database tables
  schemas/       request and response objects
  services/      business logic, CRUD and algorithms (palette history, generation, Bast index...)
  utils/         palette diff, lexicographic ranker
  scripts/       standalone scripts, not used by the API
alembic/         migrations
tests/           unit tests
```

## Getting started

Copy the example environment file and fill it in:

```sh
cp .env.example .env
```

### With Docker

```sh
docker compose up -d
docker compose exec web uv run alembic upgrade head
```

The API runs on http://localhost:8000 with hot reload, and PostgreSQL on port 5432.

### Without Docker

You need uv and a running PostgreSQL. Point `DATABASE_URL` to it (with `localhost` instead of `db`), then:

```sh
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

`uv.lock` pins every dependency, like a `package-lock.json`. To work inside the virtual environment directly: `source .venv/bin/activate`.

### Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Used by the `db` container |
| `SECRET_KEY` | Key used to sign JWTs |
| `FRONTEND_URL` | Frontend address, used in email links and sitemaps |
| `BACKEND_PUBLIC_URL` | Public address of the API, used in email links |
| `API_URL` | Public address of the API, used in the hex sitemaps (defaults to `https://api.rgbast.com`) |
| `SMTP_ENABLED` | `true` or `false` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_SSL` | SMTP server |
| `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | SMTP credentials and sender |
| `DB_POOL_RECYCLE_SECONDS` | Optional, defaults to 1800 |

Allowed CORS origins are set in `app/main.py`: rgbast.com and `localhost:5173` for local development.

### Emails in local development

Login requires a verified email address. Without SMTP (`SMTP_ENABLED=false`), no email is sent, so verify your test account by hand:

```sql
UPDATE "user" SET is_email_verified = true WHERE username = 'your_username';
```

## Migrations

The schema is managed with Alembic. Migrations are never applied when the API starts: run them after each pull that adds one.

```sh
uv run alembic upgrade head     # apply all pending migrations
uv run alembic downgrade -1     # undo the last one
uv run alembic current          # show the current revision
```

With Docker, prefix these commands with `docker compose exec web`.

### Adding a migration

1. Change or add the model in `app/models/`
2. If it is a new model, import it in `alembic/env.py`, otherwise autogenerate will not see it
3. Generate the migration:
   ```sh
   uv run alembic revision --autogenerate -m "short description"
   ```
4. Rename the file and set its `revision` to the next number (`0009`, `0010`...), with `down_revision` pointing to the previous one, to keep the numbering
5. Read the generated file: autogenerate misses partial indexes, check constraints and data backfills
6. Apply it with `uv run alembic upgrade head`, then test `downgrade`

## Tests

```sh
uv run python -m unittest discover -s tests
```

The tests cover the Bast index, the palette diff, palette generation and profile colors.

## Deployment

Each push on `main` runs the GitHub Actions workflow in `.github/workflows/deploy.yml`, which connects to the VPS over SSH and runs the `deploy-backend` script there.

Required secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, and optionally `VPS_PORT` and `VPS_FINGERPRINT`.

In production:
- `docker-compose.production.yml` runs the API (bound to `127.0.0.1:8000`) and PostgreSQL, both with health checks
- `nginx.conf` handles HTTPS with Let's Encrypt certificates and proxies requests to the API
- `deploy-backend` has to run `alembic upgrade head`, otherwise run it by hand after a deploy that includes a new migration

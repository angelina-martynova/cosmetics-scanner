# Cosmetics Scanner

A web application for analyzing cosmetic product ingredients. Upload a photo of a product label — get a detailed report about each ingredient and its safety level.

## What it does

The user uploads a photo of a cosmetic product label. The app reads the text from the image, finds each ingredient in the database, and shows a report: what the substance is, what category it belongs to, how risky it is, and whether it is allowed by EU regulations and EWG standards.

## How it works

**Text recognition (OCR)** — the app extracts text from the label photo using Tesseract OCR. Before recognition, the image goes through preprocessing: contrast adjustment, noise reduction, and skew correction. EasyOCR and TrOCR can also be connected as alternative OCR engines.

**Ingredient analysis (NLP)** — the recognized text is parsed into separate ingredients. Each one is searched in the database using exact match, fuzzy search (RapidFuzz), and keyword-based classification. Unknown substances are automatically checked through external APIs (Open Food Facts, PubChem, CIR).

**Safety assessment** — each ingredient gets a risk level (safe / moderate / hazardous) based on EWG rating, GHS classification, and EU regulations. The overall product safety status is calculated automatically.

## Tech stack

- **Backend:** Flask, PostgreSQL, SQLAlchemy
- **OCR:** Tesseract (main), EasyOCR, TrOCR (optional)
- **Image processing:** PIL/Pillow, OpenCV
- **NLP:** regex parsing, RapidFuzz, keyword classification, ML filter
- **External APIs:** Open Food Facts, PubChem, CIR (Cosmetic Ingredient Review)
- **Export:** PDF reports (ReportLab)
- **Authentication:** Flask-Login

## Key features

- Upload a label photo or enter ingredient text manually
- Multi-engine OCR with image preprocessing
- Automatic ingredient recognition and classification
- Risk assessment based on EU regulations and EWG ratings
- Scan history with PDF export
- User system with admin panel for ingredient verification

## Configuration & running

All configuration comes from environment variables. Copy `.env.example` to `.env`
and fill it in. `APP_ENV` selects the config profile: `development` (default),
`production`, or `testing`.

- `SECRET_KEY` and `DATABASE_URL` are **required** when `APP_ENV=production` — the
  app refuses to start without them (no insecure defaults).
- In `development` a local SQLite file and a throwaway secret are used, so no
  `.env` is strictly required for local work.

### Local development

```bash
pip install -r requirements.txt
python backend/app.py            # run from the repository root
```

`backend/app.py` uses Flask's built-in server and is for local development only.

### Production

Run a WSGI server from the repository root:

```bash
export APP_ENV=production
export SECRET_KEY=...            # python -c "import secrets; print(secrets.token_hex(32))"
export DATABASE_URL=postgresql://cosmetics_app:PASSWORD@host:5432/cosmetics_db
gunicorn app:app --pythonpath backend -w "$GUNICORN_WORKERS" -b 0.0.0.0:"$PORT" --timeout "$GUNICORN_TIMEOUT"
```

A `Procfile` with the same command is included.

### Creating an admin

There is **no** auto-created admin account. After initializing the database,
create one explicitly:

```bash
cd backend
flask --app app create-admin            # prompts for email and password
# or non-interactively:
flask --app app create-admin --email you@example.com --password '...'
```

### Rate limiting

`/api/analyze`, `/api/analyze_text`, `/api/upload_text_file` are limited per day
(`SCAN_DAILY_LIMIT`); `/api/login` and `/api/register` per minute
(`AUTH_RATE_LIMIT`); `/api/external/search` per minute (`EXTERNAL_SEARCH_LIMIT`).
Limits are counted per `user_id` for authenticated users and per IP for guests.

**`GUNICORN_WORKERS` and `RATELIMIT_STORAGE_URI` must match:** with
`GUNICORN_WORKERS > 1` the default `memory://` gives each worker its own
counter, so the effective limit is multiplied by the number of workers. More
than one worker ⇒ `RATELIMIT_STORAGE_URI` **must** be a shared store, e.g.
`redis://localhost:6379` (uncomment `redis` in `requirements.txt`). The app
prints a startup warning if this is misconfigured.

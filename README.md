# Violation-Detection-and-Fine-Management-Web-Application
This web application detects the seat belt violation via an API(Pre-defined dataset) - rest of the violation can be added manually. And has two separate dashboards to handle the fine management.

This README explains what the web application does, how to install and run it (concrete commands assuming a Python + Flask backend), and a step‑by‑step walkthrough of the runtime behavior and user flows.

Repository: https://github.com/Hashan-M96/Violation-Detection-and-Fine-Management-Web-Application  
Description: This web application detects seat belt violations via an API (pre-defined dataset) — other violation types can be added manually — and provides two separate dashboards to manage fines.

---

## Table of contents
- Overview
- Key features
- Tech stack & architecture
- Prerequisites
- Installation (concrete commands)
- Configuration / environment variables
- Running the app (development & production)
- Step‑by‑step walkthrough of what the app does (user and internal flows)
- Extending the app (add new violation types, swap detection API)
- Troubleshooting & tips
- License & contact

---

## Overview
This web application provides:
- Automated detection of seat belt violations through a detection API (uses a pre-defined dataset).
- Manual entry for other violation types.
- Two dashboards for fine management (separate roles/privileges): typically Officer and Admin (or similar).
- Storage and management of detected violations and issued fines.

---

## Key features
- Automated seatbelt violation detection via API.
- Manual violation creation and editing.
- Fine issuance, search and management via dashboards.
- Simple web UI (HTML/CSS) and Python backend.
- Basic persistence (SQLite by default) and REST API endpoints for detection and management.
- Role-based dashboards (two separate dashboard views).

---

## Tech stack & architecture (assumptions)
- Backend: Python (Flask)
- Frontend: HTML + CSS + minimal JS (static templates)
- Database: SQLite (default for dev); configurable to PostgreSQL/MySQL for production
- Detection API: HTTP API (pre-defined dataset). The app calls this API for automated seatbelt detection.
- Typical structure:
  - app.py / run.py (Flask app entry)
  - /templates (HTML)
  - /static (CSS, JS)
  - /models (SQLAlchemy models)
  - /routes (Flask blueprints / views)
  - requirements.txt

---

## Prerequisites
- Python 3.8+ (3.10 recommended)
- git
- (Optional) virtualenv or python -m venv
- curl (for quick API checks)

---

## Installation (concrete commands)

1. Clone the repository
   ```
   git clone https://github.com/Hashan-M96/Violation-Detection-and-Fine-Management-Web-Application.git
   cd Violation-Detection-and-Fine-Management-Web-Application
   ```

2. Create and activate a virtual environment
   - macOS / Linux:
     ```
     python3 -m venv venv
     source venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

3. Install Python dependencies
   - If repository has requirements.txt:
     ```
     pip install -r requirements.txt
     ```
   - If not, a minimal set of packages you can install:
     ```
     pip install flask sqlalchemy flask-migrate requests python-dotenv gunicorn
     ```

4. Create the database (SQLite example)
   - If the app uses Flask-Migrate:
     ```
     export FLASK_APP=app.py        # or set FLASK_APP in .env for Windows: set FLASK_APP=app.py
     flask db init
     flask db migrate -m "Initial migration"
     flask db upgrade
     ```
   - If no migrations, an alternative is to run a provided script (example):
     ```
     python scripts/create_db.py
     ```
   (Adjust these commands to whatever migrations / create-db flow the repo includes.)

---

## Configuration / environment variables
Create a `.env` file in the project root (or set env vars in your shell). Example `.env`:
```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///data/dev.db
DETECTION_API_URL=https://detection-api.example.com/predict
DETECTION_API_KEY=optional-api-key
```

- FLASK_APP: Flask entrypoint (app.py)
- DATABASE_URL: SQLAlchemy URL (sqlite or a production DB URI)
- DETECTION_API_URL: remote or local detection API endpoint used for seatbelt detection
- DETECTION_API_KEY: if API requires authentication

Load .env automatically (use python-dotenv or the repo's config loader).

---

## Running the app

Development server (Flask):
```
# Activate venv first
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```
Windows PowerShell:
```
$env:FLASK_APP="app.py"
$env:FLASK_ENV="development"
flask run --host=0.0.0.0 --port=5000
```

Direct run (if app defines run block):
```
python app.py
```

Production (Gunicorn example):
```
gunicorn --bind 0.0.0.0:8000 app:app
```
Use a proper WSGI server + reverse proxy (nginx) for production.

---

## API examples

1. Call detection API via app (example cURL to your app)
```
curl -X POST "http://localhost:5000/api/detect" \
  -F "image=@/path/to/photo.jpg"
```

2. Directly call the external detection API (if needed)
```
curl -X POST "https://detection-api.example.com/predict" \
  -H "Authorization: Bearer $DETECTION_API_KEY" \
  -F "image=@/path/to/photo.jpg"
```

3. Create a violation manually (example):
```
curl -X POST "http://localhost:5000/api/violations" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "speeding",
    "vehicle_number": "ABC-1234",
    "location": "Main Street",
    "timestamp": "2025-10-21T09:00:00Z",
    "notes":"Driver speeding"
  }'
```

---

## Step‑by‑step walkthrough — what the web app does

This section describes the typical flows (both user-facing and internal behavior). Replace role names and endpoint paths with those used in the repo if different.

1. Initialize and configure
   - Developer sets environment variables (DETECTION_API_URL, DATABASE_URL, SECRET_KEY).
   - App boots, connects to DB, and (optionally) runs migrations.

2. Upload or ingest images/videos for detection
   - Officer or automated process uploads an image (single frame) to the app via the web UI or API endpoint /api/detect.
   - The app receives the image and optionally stores a copy (for evidence).

3. The app calls the detection API
   - Backend sends the image to the configured DETECTION_API_URL with any required auth.
   - The detection API returns predictions in JSON (e.g., bounding boxes, class labels such as "seatbelt_on"/"seatbelt_off", confidence scores).

4. Parse detection results and create a violation record
   - If the detection result indicates a seat belt violation (e.g., label "seatbelt_off" above a confidence threshold), the app:
     - Creates a new Violation record in the DB with fields: violation_type, confidence, image_path, timestamp, location (if present), vehicle_number (if OCR or manual).
     - Optionally stores bounding box and raw detection JSON in a evidence field.

5. Notify / present result in UI
   - The app redirects the user to a violation review page or returns JSON with detection results.
   - The Officer can review the detection, confirm or reject it, add notes, attach vehicle or driver info, or edit fields.

6. Manual violation creation / editing
   - For violations that the automated system doesn't support (e.g., illegal parking, driving without license), Officers can create violations manually via a form.
   - Form submission creates a Violation record similar to automated ones.

7. Fine issuance and management via dashboards
   - The application provides two dashboards (examples):
     - Officer Dashboard: view recent detections, confirm/reject violations, add fines, attach evidence.
     - Admin Dashboard: view all violations, manage fine rules (amounts per violation type), review appeal statuses, export reports.
   - Issuing a fine typically creates a Fine record linked to the Violation, storing amount, status (issued/paid/overdue), and payment details.

8. Payment tracking and status updates
   - The Admin or Officer can mark fines as paid or overdue. The application updates statuses and logs timestamps.
   - Export or reporting features allow admins to generate CSV or PDF lists of fines.

9. Search, filters and reporting
   - Users can search violations by vehicle number, date range, location or status.
   - Admins can filter by violation type and generate summary statistics (counts, total fines collected).

10. Audit & evidence retention
    - The system retains the original images and detection metadata for audit purposes (policy-configurable retention period).

---

## Extending the app

- Add new violation types:
  - Update the database schema/model to include the new type (if violation_type is fixed-choice).
  - Add UI elements (forms and dropdowns) and update rules for fines.
  - Add detection logic (new API or extend current API) or create manual-only entry.

- Swap detection API:
  - Update DETECTION_API_URL and adapt response parsing logic in the detection handler to match the new API's response format.

- Use a production DB:
  - Set DATABASE_URL to a PostgreSQL URI (postgresql://user:pass@host:port/dbname).
  - Run migrations and ensure proper firewall/connection settings.

---

## Troubleshooting & tips
- If app fails to start: check FLASK_APP and FLASK_ENV variables and ensure virtualenv is activated.
- Detection returns no results: verify DETECTION_API_URL and API key; test external API directly with curl.
- Database errors: confirm DATABASE_URL is correct, run migrations, and check that the DB file permissions allow writing.
- For large image uploads, ensure web server and reverse proxy have appropriate client_max_body_size settings (nginx).

---

## Security & privacy notes
- Store SECRET_KEY securely (do not commit .env with secrets).
- If storing images, ensure retention policies comply with local privacy regulations.
- Restrict detection API keys and database credentials in production.

---

## Deployment recommendations
- Use Gunicorn + systemd + nginx as reverse proxy.
- Put static assets behind a CDN or serve via nginx.
- Use managed DB service for production (Postgres) and configure backups.
- Use HTTPS with a valid TLS certificate.

---

## Contact & contribution
- Repo owner: Hashan-M96 (https://github.com/Hashan-M96)
- To contribute, open PRs and follow any contributing guidelines in the repo.

---

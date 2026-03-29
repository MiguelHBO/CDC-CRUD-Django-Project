# CDC Audit Service — Portfolio Demo

A **Change Data Capture (CDC) pipeline** built with Django and DuckDB.  
Every INSERT, UPDATE, and DELETE on the e-commerce data is captured at column-level granularity, stored in an analytical store, and visualised in real-time.

This project simulates how a real-world data platform can:

- capture **database changes in near real time**
- process them into an **analytical audit layer**
- separate **operational** and **analytical** workloads
- expose the result through a **live monitoring dashboard**

Every **INSERT**, **UPDATE**, and **DELETE** performed on the e-commerce entities is tracked at **column-level granularity**, stored in an analytical store, and visualized in the browser.

---

## About this project

This repository is **not just a study project**.

It is a **portfolio-safe recreation** of a **real CDC pipeline**, implemented by me as part of my professional work.

The original production solution is based on a real business system database (SAS platform) and follows a modern **data engineering / medallion architecture** approach:

- CDC is collected directly from **source database tables**
- the processing logic is handled by a **Python job**
- this job runs in **Azure Kubernetes Service (AKS)** as a scheduled workload
- the execution happens **every 5 minutes**
- raw and transformed data flows through a **medallion-style processing approach**
- the processed output is generated in **Parquet**
- the final dataset is loaded into a **Microsoft Fabric Warehouse**
- the data is then consumed for **analytics, auditing, and reporting**
Because the original implementation is part of a real production environment, this public repository recreates the same **core engineering concepts and architecture patterns** using tools that can run locally and safely for portfolio demonstration.

In other words:

> **The business logic and architectural reasoning are based on a real production system.  
> The infrastructure and tooling were adapted to make the project portable, reproducible, and safe to publish.**

---

## Production architecture that inspired this demo

The original production version follows a pipeline concept similar to this:

```
Source Database (SAS)
        │
        ▼
Change Data Capture (CDC)
        │
        ▼
Python scheduled processing job
(AKS Job / runs every 5 minutes)
        │
        ▼
Medallion-style transformation
        │
        ▼
Parquet generation
        │
        ▼
Microsoft Fabric Warehouse
        │
        ▼
Consumption / Audit / Analytics
```

---

## What this demonstrates

| Concept | Production (original) | This demo |
|---|---|---|
| Change capture | SQL Server CDC (log-based) | Django `post_save` / `post_delete` signals |
| Analytical store | Microsoft Fabric Warehouse | DuckDB (local file) |
| Bulk load | Parquet + COPY INTO via OneLake | Direct DuckDB insert |
| LSN / cursor control | `dbo.cdc_lsn_control` table | Auto-increment `cdc_id` |
| Scheduling | AKS CronJob | Django dev server (immediate) |
| Containerisation | Docker + AKS | Docker Compose |

The signal-based approach captures the same information as log-based CDC: **which column changed, from what value, to what value, at what time**. The difference is that log-based CDC reads the DB transaction log without touching the application — signals are application-level hooks. Both produce the same audit trail schema.

---

## Quick start — 3 commands

```bash
git clone https://github.com/MiguelHBO/CDC-CRUD-Django-Project.git
cd cdc-audit-demo
docker compose up --build
```

Open **http://localhost:8000** — the app loads with seed data and a pre-populated audit trail.

> No accounts. No API keys. No cloud services. Everything runs locally.

---

## Running without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed          # populates demo products, orders, and audit events
python manage.py runserver
```

---

## Project structure

```
cdc-audit-demo/
├── cdc_project/           # Django project config (settings, urls, wsgi)
├── ecommerce/             # CRUD app — Products and Orders
│   ├── models.py          # Product, Order
│   ├── views.py           # list / create / edit / delete views
│   ├── forms.py           # ModelForms
│   └── management/
│       └── commands/
│           └── seed.py    # Demo data + simulated audit events
├── audit/                 # CDC pipeline app
│   ├── cdc.py             # ★ Core: signal handlers + DuckDB writer
│   ├── apps.py            # Wires signals on app ready()
│   ├── views.py           # Dashboard + JSON polling endpoint
│   └── urls.py
├── static/css/main.css    # Dark theme UI
├── templates/base.html    # Nav + message toasts
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## How the CDC pipeline works

```
User action (browser)
      │
      ▼
Django ORM  ──pre_save──►  snapshot old state
      │
      │  (DB write)
      │
      ▼
post_save / post_delete signal
      │
      ▼
audit/cdc.py  ──  diff columns  ──►  write_event()
                                          │
                                          ▼
                                     DuckDB  (audit_log.duckdb)
                                     cdc_audit_log table
                                          │
                                          ▼
                                     /audit/ dashboard
                                     (polled every 5s)
```

### Column-level diff (UPDATE granularity)

For every UPDATE, `handle_pre_save` snapshots the current DB row before the write.  
After the write, `handle_post_save` diffs the old and new snapshots and emits **one audit row per changed column** — the same granularity produced by SQL Server CDC.

```python
# Example: changing an order status from "pending" → "processing" produces:
{
  "table_name":  "Order",
  "entity_id":   42,
  "operation":   "UPDATE",
  "column_name": "status",
  "old_value":   "pending",
  "new_value":   "processing",
  "change_date": "2024-11-15 14:32:01"
}
```

### DuckDB as the analytical store

DuckDB is used instead of a hosted warehouse because it:
- Runs in-process — zero server setup
- Supports full SQL including window functions and `INTERVAL` queries
- Handles analytical aggregations (chart queries) faster than SQLite
- Uses the same interface as production DuckDB/Fabric queries

In production, `write_event()` would be replaced by the Parquet + COPY INTO batch loader.

---

## Audit dashboard

- **Stats row** — total events, per-operation counts
- **Operations by table** — grouped bar chart (Chart.js)
- **Timeline** — line chart of events per hour over the last 24h
- **Live event log** — table that polls `/audit/api/recent/` every 5s; new rows animate in without page reload
- **Column diff** — `old_value → new_value` displayed inline for UPDATE events

---

## Tech stack

| Layer | Technology |
|---|---|
| Web framework | Django 5 |
| CDC mechanism | Django signals (`pre_save`, `post_save`, `post_delete`) |
| Operational DB | SQLite (swappable to PostgreSQL via `DATABASES` in settings) |
| Analytical store | DuckDB |
| Charts | Chart.js 4 |
| Styling | Vanilla CSS (dark theme, IBM Plex font) |
| Static files | WhiteNoise |
| Container | Docker + Compose |

---

## Swapping SQLite for PostgreSQL

Edit `cdc_project/settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "cdc_demo"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}
```

Then `pip install psycopg2-binary` and run `python manage.py migrate`.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | `dev-secret-key-…` | Django secret key |
| `DEBUG` | `true` | Debug mode |
| `DUCKDB_PATH` | `audit_log.duckdb` | Path to the DuckDB file |

Copy `.env.example` to `.env` for local development.

---

## Production notes

This demo runs Django's built-in dev server intentionally — it keeps the setup to a single `docker compose up`. For a real deployment:

- Replace `runserver` with `gunicorn cdc_project.wsgi` in the Dockerfile `CMD`
- Set `DEBUG=false` and configure `ALLOWED_HOSTS`
- Use a persistent volume or managed PostgreSQL for the operational DB
- The DuckDB file can be replaced with any SQLAlchemy-compatible analytical DB

---

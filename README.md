# IT Asset & Inventory Management System

An internal web app that keeps one trusted record of the company's IT equipment:
what we own, where it is, who has it, and what needs attention.

- **Requirements:** [documentation/IT_Asset_Inventory_Management_PRD_v1.pdf](documentation/IT_Asset_Inventory_Management_PRD_v1.pdf)
- **Build plan:** [documentation/IT_Asset_Inventory_Build_Plan_Phases.docx](documentation/IT_Asset_Inventory_Build_Plan_Phases.docx)
- **Decisions log:** [documentation/decisions.md](documentation/decisions.md)

**Current state:** Phase 1, Slice 1.3: server-side login and roles (no screens yet).

---

## 1. What is in this repository

```
backend/    Python + FastAPI server (the API) - talks to PostgreSQL
frontend/   React app (the screens) - runs in the browser, talks to the backend
documentation/  PRD, build plan, decisions
scripts/    dev-db: the project's own local PostgreSQL server (development only)
.dev-db/    that server's data folder (created by scripts\dev-db init, never committed)
docker-compose.yml  Alternative local database using Docker
```

How a request travels:

```
Browser (React, :5173)  --HTTP-->  FastAPI (:8000)  --SQLAlchemy-->  PostgreSQL dev server (:5433)
```

The browser never talks to the database directly; everything goes through the API.

---

## 2. Software you need (one time)

| Tool | Version | Check with |
|---|---|---|
| Python | 3.11 or newer | `python --version` |
| Node.js | 22.12+ (LTS) | `node --version` |
| PostgreSQL programs | 17 or newer | Folder `C:\Program Files\PostgreSQL\<version>\bin` exists |
| Git | any recent | `git --version` |

You do **not** need the `postgres` password or admin rights. The project runs its own separate
PostgreSQL server using the programs already installed (section 3). Docker is an optional
alternative.

All commands below are for **Windows PowerShell**, starting from the repository folder.

---

## 3. Set up the database (one time)

We use **two** databases, both owned by a database user called `itam_app`:

- `itam_dev`: your everyday development data.
- `itam_test`: used only by the automated tests (they may wipe it).

The app logs in as `itam_app`, never as the all-powerful `postgres` superuser. The password
`itam_dev_password` is for local development only. Never use it on a real server.

### Option 1 (default): the project's own dev database server

[scripts/dev-db.ps1](scripts/dev-db.ps1) runs a **separate** PostgreSQL server just for this
project, using the PostgreSQL programs already on the PC:

- Its data lives in `.dev-db\` inside the repository. That folder is in `.gitignore`, so it is
  never committed.
- It listens on port **5433**, from this computer only.
- Any other PostgreSQL on the PC (for example the Windows service on port 5432) and its data are
  **never touched**.

From the repository folder:

```powershell
scripts\dev-db init      # one time: create the server, user itam_app, itam_dev and itam_test
scripts\dev-db status    # is it running?
```

| Task | Command |
|---|---|
| Start it (needed after every Windows restart) | `scripts\dev-db start` |
| Stop it (data is kept) | `scripts\dev-db stop` |
| Check it | `scripts\dev-db status` |

> `init` is safe to run again: it only creates what is missing.
> To start completely fresh: `scripts\dev-db stop`, delete the `.dev-db` folder, then
> `scripts\dev-db init`. This deletes **only** this project's development data.

`backend\.env.example` already points at this server (port 5433).

### Option 2: PostgreSQL in Docker

PostgreSQL runs inside a Docker **container**: an isolated mini-computer that Docker starts and
stops for you. Everything is described in [docker-compose.yml](docker-compose.yml), which also
creates both databases automatically. It uses the same port (5433), user and password, so
`.env` needs no change. Don't run it at the same time as option 1, because both use port 5433.

1. Start **Docker Desktop** (from the Start menu) and wait until it says it is running.
2. From the repository folder, start the database:

   ```powershell
   docker compose up -d
   ```

   The first time, Docker downloads the PostgreSQL image (about 150 MB). `-d` means "run in the
   background".

3. Check it is ready. The `STATUS` column should say `healthy`:

   ```powershell
   docker compose ps
   ```

| Task | Command |
|---|---|
| Stop the database (data is kept) | `docker compose down` |
| Start it again | `docker compose up -d` |
| **Delete all data** and start fresh | `docker compose down -v` then `docker compose up -d` |

> The database listens on port **5433** (not the usual 5432), and only on this computer. Its
> user name and password are in `docker-compose.yml` and are for local development only.

### Option 3: an existing PostgreSQL where you know the `postgres` password

Create the user and databases there, then change **5433 to 5432** in both database lines of
`backend\.env`:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -c "CREATE ROLE itam_app WITH LOGIN PASSWORD 'itam_dev_password';" -c "CREATE DATABASE itam_dev OWNER itam_app;" -c "CREATE DATABASE itam_test OWNER itam_app;"
```

---

## 4. Backend setup

```powershell
cd backend

# 4.1 Create a virtual environment: a private folder of Python packages for this project only.
python -m venv .venv

# 4.2 Install the packages (runtime + testing).
.venv\Scripts\python -m pip install -r requirements-dev.txt

# 4.3 Create your settings file from the template.
copy .env.example .env
```

4.4 Edit `backend\.env`:

- Set `JWT_SECRET_KEY` to your own random secret (it signs login tokens). Generate one with:

  ```powershell
  .venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

- Database lines: options 1 and 2 need no change. Option 3: change `5433` to `5432` in both
  database lines.

> `.env` can hold secrets. It is listed in `.gitignore` and must never be committed.

### 4.5 Run the database migrations

A **migration** is a small versioned script that changes the database structure. Alembic keeps
track of which ones have run, so every computer ends up with exactly the same tables.

```powershell
.venv\Scripts\alembic upgrade head
```

Expected: it runs each migration, for example `Running upgrade 0001 -> 0002, Roles, employees
(minimal) and users`. Migration 0002 also adds the three roles: Admin, IT Manager, Employee.

Other useful Alembic commands (later slices):

```powershell
.venv\Scripts\alembic current                                   # which migration the DB is on
.venv\Scripts\alembic revision --autogenerate -m "add users"    # write a new migration from model changes
.venv\Scripts\alembic downgrade -1                              # undo the last migration
```

### 4.6 Start the backend

```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload
```

`--reload` restarts the server automatically when you save a file. Leave this window open.

- Health check: <http://localhost:8000/health> should show `{"status":"ok","database":"reachable"}`
- API docs (Swagger): <http://localhost:8000/docs>

If PostgreSQL is stopped, `/health` answers with status **503** and `"database":"unreachable"`.

### 4.7 Create the first Admin account (one time)

In a second PowerShell window, from the `backend` folder:

```powershell
.venv\Scripts\python -m app.scripts.create_admin
```

It asks for the Admin's email and a password (at least 12 characters; nothing shows while you
type). It only stores a secure hash of the password, never the password itself. If an active
Admin already exists, it does nothing.

**Test accounts for other roles (development only, until user management in Slice 1.6):**

```powershell
.venv\Scripts\python -m app.scripts.create_user --role Employee
.venv\Scripts\python -m app.scripts.create_user --role "IT Manager"
```

### 4.8 Log in on the API docs page

1. Open <http://localhost:8000/docs>.
2. Open **POST /api/v1/auth/login**, click **Try it out**, enter your email and password, click
   **Execute**. Copy the `access_token` value (without the quotes).
3. Click **Authorize** (top right), paste the token, click **Authorize**, then **Close**.
4. Try **GET /api/v1/auth/me** (your account) and **GET /api/v1/admin/ping**. An Admin gets
   `pong`; any other role gets **403** `forbidden`.

Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30). When that happens, log in again.

### 4.9 Run the tests

```powershell
.venv\Scripts\python -m pytest
```

The tests use `TEST_DATABASE_URL` (never your dev database) and apply all migrations to it first.
They refuse to run if `TEST_DATABASE_URL` is missing or the same as `DATABASE_URL`.

> Optional: "activating" the virtual environment (`.venv\Scripts\Activate.ps1`) lets you type
> `alembic`, `pytest`, etc. without the `.venv\Scripts\` prefix. If PowerShell blocks the script,
> just keep using the full `.venv\Scripts\...` form shown above.

---

## 5. Frontend setup

Open a **second** PowerShell window (the backend keeps running in the first).

```powershell
cd frontend

# 5.1 Install the JavaScript packages listed in package.json (creates node_modules/).
npm install

# 5.2 Create the frontend settings file.
copy .env.example .env

# 5.3 Start the development server.
npm run dev
```

Open <http://localhost:5173>. The start page should show a green box:
**"Backend: running · Database: reachable"**. A red box means the backend isn't running, or
CORS isn't allowing `http://localhost:5173` (check `CORS_ORIGINS` in `backend\.env`).

---

## 6. Settings (environment variables)

| File | Used for |
|---|---|
| `backend/.env.example` | Development template. Copy it to `backend/.env`. |
| `backend/.env.production.example` | Production template (go-live, Slice 8.5). |
| `frontend/.env.example` | Frontend template. Copy it to `frontend/.env`. **Never put secrets here**: everything in it is visible in the browser. |

`APP_ENV` (`development`, `test` or `production`) keeps the environments separate. In
`production` the backend refuses to start if `CORS_ORIGINS` contains `localhost` or `SQL_ECHO`
is on.

---

## 7. Folder guide

### backend/

| Path | Purpose |
|---|---|
| `app/main.py` | Creates the FastAPI app, sets up CORS and the error format, and plugs in each module's routes under `/api/v1`. |
| `app/core/config.py` | Reads all settings from environment variables / `.env` (pydantic-settings). |
| `app/core/database.py` | Database connection (always UTC), `Base` class, `TimestampMixin` (created/updated times) and `get_db` (one session per request). |
| `app/core/security.py` | Password hashing (Argon2) and JWT token creation/checking. |
| `app/core/errors.py` | The one error format `{"error": {code, message, details}}` and `AppError`. |
| `app/core/pagination.py` | Shared paged-list helper: `page`, `page_size`, `sort` in; `{items, total, page, page_size}` out. |
| `app/models.py` | Imports every module's tables so Alembic can see them. |
| `app/modules/<module>/` | One folder per feature: `models.py` (tables), `schemas.py` (request/response shapes), `service.py` (business logic), `routes.py` (API endpoints). |
| `app/modules/health/` | `GET /health` (no table, so no `models.py`). |
| `app/modules/auth/` | Login, `/me`, logout, plus `dependencies.py`: `get_current_user` and `require_roles(...)`, used to protect every endpoint. |
| `app/modules/users/` | `roles` and `users` tables, user schemas (never include the password hash), create-user logic. |
| `app/modules/employees/` | Minimal `employees` table (completed in Slice 2.2). |
| `app/modules/admin/` | Admin-only endpoints (`/admin/ping` test endpoint for now). |
| `app/scripts/` | Command-line tools: `create_admin` (first Admin), `create_user` (dev test accounts). |
| `docker/init-test-db.sql` | Creates the `itam_test` database the first time the Docker database starts. |
| `alembic.ini`, `alembic/` | Migration tool settings; `alembic/env.py` reads `DATABASE_URL`; `alembic/versions/` holds each migration. |
| `tests/` | Automated tests. `conftest.py` points the app at the test database and runs migrations first. |
| `requirements.txt` | Packages needed to run the backend. |
| `requirements-dev.txt` | Extra packages for development and testing. |
| `pyproject.toml` | pytest settings. |

### scripts/ and .dev-db/

| Path | Purpose |
|---|---|
| `scripts/dev-db.ps1` | Creates, starts, stops and checks the project's own PostgreSQL server (port 5433). |
| `scripts/dev-db.cmd` | Shortcut so `scripts\dev-db start` works without PowerShell script-permission prompts (applies to that one run only). |
| `.dev-db/data/` | The dev server's database files. Never commit; never edit by hand. |
| `.dev-db/postgres.log` | The dev server's log: look here if it won't start. |
| `.dev-db/superuser-password.txt` | Random password for the dev server's own `postgres` superuser (development only). |

### frontend/

| Path | Purpose |
|---|---|
| `index.html`, `src/main.jsx` | Entry point: loads React, the MUI theme and the router. |
| `vite.config.js` | Dev server settings (port 5173). |
| `src/api/` | All calls to the backend (`client.js` = one shared Axios instance). |
| `src/components/` | Reusable pieces used by many pages. |
| `src/pages/` | One file per screen. |
| `src/layouts/` | Page frames (top bar; sidebar comes in Slice 1.5). |
| `src/routes/` | Which address shows which page. |
| `src/context/` | Shared app-wide state such as the logged-in user (Slice 1.5). |
| `src/theme.js` | Shared colours and fonts (MUI theme). |

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `/health` shows `unreachable`, or `connection refused` on port 5433 | The dev database isn't running (it doesn't start with Windows). Run `scripts\dev-db start`. |
| `password authentication failed for user "itam_app"` or `database "itam_test" does not exist` | Run `scripts\dev-db init` (it adds anything missing). Check `.env` uses port `5433`, or copy `.env.example` to `.env` again. |
| `scripts\dev-db start` says `Server did not start` | Read the last lines of `.dev-db\postgres.log`. Port 5433 may be in use by the Docker database (`docker compose down`). |
| `failed to connect to the docker API` (option 2 only) | Docker Desktop isn't running. Start it and wait until it's ready. |
| `Port 5173 is in use` | Another `npm run dev` is still running; close it. |
| `pytest` exits with `TEST_DATABASE_URL is not set` | Add `TEST_DATABASE_URL` to `backend\.env`. |
| Server won't start: `jwt_secret_key ... Field required` or `at least 32 characters` | Add a `JWT_SECRET_KEY` to `backend\.env` (step 4.4). |
| `relation "users" does not exist` | Run the migrations: `.venv\Scripts\alembic upgrade head`. |
| Swagger says `401 invalid_token` | The token expired or was pasted with quotes. Log in again and paste only the token. |

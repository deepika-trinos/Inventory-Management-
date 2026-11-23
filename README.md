# IT Asset & Inventory Management System

An internal web app that keeps one trusted record of the company's IT equipment:
what we own, where it is, who has it, and what needs attention.

- **Requirements:** [documentation/IT_Asset_Inventory_Management_PRD_v1.pdf](documentation/IT_Asset_Inventory_Management_PRD_v1.pdf)
- **Build plan:** [documentation/IT_Asset_Inventory_Build_Plan_Phases.docx](documentation/IT_Asset_Inventory_Build_Plan_Phases.docx)
- **Decisions log:** [documentation/decisions.md](documentation/decisions.md)

**Current state:** Phase 1 (Foundation) complete: login, roles, audit log, app shell and Admin
user management. **Phase 2 (Master data) complete and signed off (2026-11-12):** asset
categories (2.1), employees (2.2; every Employee-role login is linked to an employee record),
vendors (2.3) and bulk stock items (2.4). See
[documentation/Phase2_WrapUp.md](documentation/Phase2_WrapUp.md). **Phase 3 (Purchase and
receiving) complete and signed off (2026-11-20):** draft purchases (3.1), receiving one-by-one
items as assets AST-000001, ... (3.2), by-quantity items into stock with a permanent movement
history (3.3) and purchase history (3.4: purchase list with date-range filter, purchase detail
page, each vendor's purchase history). See
[documentation/Phase3_WrapUp.md](documentation/Phase3_WrapUp.md). **Phase 4 (Asset and
inventory operations) started:** the asset register (4.1: **Assets** page with search by asset
ID, serial number or name, category / status / location filters and server-side paging; asset
page `/assets/AST-000001` with details, purchase and history) is signed off (2026-11-20).
Edit and retire assets (4.2: **Edit** the allowed details, **Retire…** with a required reason,
every change in the asset's history) is signed off (2026-11-22). Stock balances (4.3: **Low stock**
badge and filter on Inventory, stock item page `/inventory/:id` with its movement history) is signed
off (2026-11-23). Next: Slice 4.4 (stock issue and adjustment; owner answers A4–A5 needed first).
Business pages not built yet show "Coming soon" until their phase.

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
Browser (React, :3000)  --HTTP-->  FastAPI (:8000)  --SQLAlchemy-->  PostgreSQL dev server (:5433)
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
Migration 0004 adds the `asset_categories` table (Slice 2.1). Migration 0005 completes the
`employees` table (department, designation, phone; case-insensitive unique employee ID and work
email) and keeps existing rows (Slice 2.2). Migration 0006 adds the `vendors` table (Slice 2.3). Migration 0007 adds the `stock_items` table
(Slice 2.4). Migration 0008 adds the `purchases` and `purchase_lines` tables and the
`purchase_number_seq` sequence behind PUR-000001, PUR-000002, ... (Slice 3.1). Migration 0009
adds the `assets` table and the `asset_code_seq` sequence behind AST-000001, AST-000002, ...,
with serial numbers unique ignoring case (Slice 3.2). Migration 0010 adds the append-only
`stock_movements` table (Slice 3.3): every change to a stock item's balance, with its type,
quantity, balance after, date and responsible user; a database trigger blocks changes and deletes.
Migration 0011 adds `received_by_user_id` and `received_at` to `purchases` (Slice 3.4: who
received a purchase and when it was saved), filled in for earlier receipts from their
`purchase.received` audit row. Migration 0012 adds `retired_at`, `retired_by_user_id` and
`retire_reason` to `assets` (Slice 4.2: who retired an asset, when and why; empty unless retired).

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

**Other users:** log in as the Admin and use **Users → Create user** in the app (section 5).

For quick development test accounts you can also use (refuses to run in production):

```powershell
.venv\Scripts\python -m app.scripts.create_user --role "IT Manager"
.venv\Scripts\python -m app.scripts.create_user --role Employee --employee-code EMP-001
```

Since Slice 2.2 an **Employee** login must be linked to an employee record: add the employee on
the **Employees** page first, then pass its employee ID with `--employee-code`.

**Check who changed whose role** (audit log):

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -p 5433 -U itam_app -d itam_dev -f scripts\sql\recent_role_changes.sql
```

The password is the development database password in `backend\.env` (`itam_dev_password`).

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

Frontend tests (Vitest + React Testing Library, decision T1) run from the `frontend` folder:

```powershell
cd ..rontend
npm test
```

They need no backend or database: the server is replaced by stand-ins. `npm run test:watch`
re-runs them on every save.

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

Open <http://localhost:3000>. You'll see the **Sign in** page. Log in with the Admin from step
4.7 (or a test account). Each role sees its own menu:

| Role | Menu |
|---|---|
| Admin | Dashboard, Assets, Inventory, Categories, Vendors, Purchases, Employees, Assignments, Maintenance, Reports, Users, Audit Log |
| IT Manager | The same, without Users and Audit Log |
| Employee | My Dashboard, My Assets, My Requests |

Pages not built yet say **Coming soon**. The dashboard shows a green box,
**"Backend: running · Database: reachable"**. A red box means the backend isn't running, or CORS
isn't allowing `http://localhost:3000` (check `CORS_ORIGINS` in `backend\.env`).

**Staying logged in:** the login token is kept in the browser tab's *session storage*. Refreshing
the page keeps you logged in; closing the tab logs you out; each new tab needs its own login.
Tokens expire after 30 minutes, after which you're sent back to Sign in.

**Component gallery (development only):** <http://localhost:3000/dev/components> lets you try
the table, badges, form fields, confirm box, messages and date format. It isn't in the menu and
isn't included in production builds.

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
| `app/core/text.py` | Shared clean-up for typed-in fields: trim text, required text, phone check (B22). Used by employees and vendors. |
| `app/core/pagination.py` | Shared paged-list helper: `page`, `page_size`, `sort` in; `{items, total, page, page_size}` out. |
| `app/models.py` | Imports every module's tables so Alembic can see them. |
| `app/modules/<module>/` | One folder per feature: `models.py` (tables), `schemas.py` (request/response shapes), `service.py` (business logic), `routes.py` (API endpoints). |
| `app/modules/health/` | `GET /health` (no table, so no `models.py`). |
| `app/modules/auth/` | Login, `/me`, logout, plus `dependencies.py`: `get_current_user` and `require_roles(...)`, used to protect every endpoint. |
| `app/modules/inventory/` | Items tracked **by quantity** (Slice 2.4): `/api/v1/stock-items` for Admin and IT Manager (list with name search and category/status filters; get, create, edit, activate/deactivate). Category must be an **active "by quantity" (bulk)** category; name unique within its category; fixed unit list; reorder threshold 0 or more. `quantity_on_hand` is read-only: only stock movements change it. **Stock movements (Slice 3.3):** the append-only `stock_movements` table (types receipt / issue / adjustment_in / adjustment_out / opening); `record_movement()` is the one shared way to change stock (same transaction as the balance, never below 0: `insufficient_stock`), `lock_stock_items()` row-locks items first. The unit locks once any movement exists. Deactivation only at zero stock. Never deleted. Every change audited. **Stock balances (Slice 4.3):** every stock item response has `low_stock` (active and quantity on hand at or below the reorder threshold; calculated, never stored); `GET /stock-items?low_stock=true|false` filters (combines with search, category, status); `GET /stock-items/{id}/movements` is the item's movement history, newest saved first, with type, direction, signed change, balance after, business date, saved at, who, reason and the receipt's purchase. No new way to change stock. |
| `app/modules/vendors/` | Vendors (Slice 2.3): `/api/v1/vendors` for Admin and IT Manager (list with search by name, contact person, email or phone and a status filter; get, create, edit, activate/deactivate). Only the name is required; names are unique ignoring case. Never deleted (BR-12, VEN-05). `ensure_vendor_active()` blocks inactive vendors for new purchases (used by purchases since Slice 3.1). Every change audited. |
| `app/modules/purchases/` | Purchases (Slice 3.1): `/api/v1/purchases` for Admin and IT Manager (list with search by reference number, vendor name or purchase number and status/vendor filters; get one with its lines; create a **draft**; edit or cancel a draft). Numbers PUR-000001... made by the system. Vendor, stock items and categories must be active; reference unique per vendor ignoring case (cancelled ones excepted); date not in the future; at least one line; line totals and the total calculated by the server. Drafts and cancelled purchases never change stock or create assets. No delete. Every change audited. **Receiving (Slice 3.2):** `POST /api/v1/purchases/{id}/receive` receives a draft in one step (received date; per line 0 to ordered, with the details of each unit); each unit becomes an asset, the purchase becomes Received (final); all in one transaction with `purchase.received` and `asset.created` audit rows. **By-quantity lines (Slice 3.3):** send the received quantity only; each line above 0 adds one `receipt` stock movement and raises the item's balance (mixed purchases in one step; a deactivated stock item refuses the receipt). **History (Slice 3.4):** the list also filters by purchase-date range (`date_from`, `date_to`, both days included) and sorts by received date; a vendor's purchase history is the same list with `vendor_id` (newest purchase date first; unknown vendor 404; inactive vendors included). `GET /purchases/{id}` adds the vendor's contact details, each line's stock movements, and who received it and when. |
| `app/modules/assets/` | Assets tracked **one by one** (Slice 3.2): the `assets` table (asset ID AST-000001... from a database sequence; serial number unique ignoring case; model required; brand, warranty expiry, location optional; status Available / Assigned / Under Maintenance / Damaged / Retired). `GET /api/v1/assets/{id or asset ID}` for Admin and IT Manager. **Asset register (Slice 4.1):** `GET /api/v1/assets` (search by part of the asset ID, serial number or name, any case; filters `category_id` (unknown: 404 `category_not_found`), `status`, `location` (whole location, any case); sortable; newest asset ID first), `GET /api/v1/assets/locations` (locations in use, for the filter), `GET /api/v1/assets/{id or asset ID}/history` (the asset's audit log rows, newest first, paged). One asset's purchase now includes `vendor_id`. **Edit and retire (Slice 4.2):** `PATCH /api/v1/assets/{id or asset ID}` changes only name, brand, model, serial number (still unique), location and warranty expiry (anything else, status included: 422 `validation_error`); `POST /api/v1/assets/{id or asset ID}/retire` with a required reason (up to 500) only from Available or Damaged (`asset_not_retirable`), stores who / when / why on the asset; a retired asset cannot be edited or retired again (`asset_retired`). Each change writes `asset.updated` (old and new values) or `asset.retired` (reason) in the same transaction, with a row lock against two changes at once. Manual entry is 4.5. No delete. |
| `app/modules/users/` | `roles` and `users` tables; Admin-only `/api/v1/users` endpoints (list, create, edit, role, activate/deactivate); safety rules (not yourself, last Admin); every change audited. |
| `app/modules/categories/` | Asset categories (Slice 2.1): `/api/v1/categories` for Admin and IT Manager (list with search/filters, get, create, edit, activate/deactivate). Each is tracked **one-by-one** (`serialized`) or **by quantity** (`bulk`). Never deleted (BR-12). `ensure_category_selectable()` blocks inactive categories for new records (used from Slice 2.4); the tracking type locks once stock items, purchase lines or assets use the category (stock items from 2.4, purchase lines from 3.1, assets from 3.2). Every change audited. |
| `app/modules/employees/` | Employees (Slice 2.2): `/api/v1/employees` for Admin and IT Manager (list with search by ID/name/department, filters by status, department and has-login; `/departments` for suggestions; get, create, edit, activate/deactivate). Never deleted (BR-12). Deactivating an employee also deactivates the linked login. Every change audited. |
| `app/modules/admin/` | Admin-only endpoints (`/admin/ping` test endpoint for now). |
| `app/modules/audit/` | Append-only audit log: `models.py` (table), `actions.py` (every action name), `service.py` (`audit.record(...)`: writes in the caller's transaction and strips secrets). |
| `app/scripts/` | Command-line tools: `create_admin` (first Admin), `create_user` (dev test accounts; `--employee-code` links an employee, required for the Employee role). `reset_password` (strictly development only: runs only when `APP_ENV=development` is explicitly set; refuses production, test and a missing `APP_ENV`; new password for an existing login, asked privately; audited; D8). |
| `scripts/sql/` | Handy read-only SQL queries, e.g. `recent_role_changes.sql`. |
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
| `index.html`, `src/main.jsx` | Entry point: loads React, the theme, the router, notifications and login state. |
| `vite.config.js` | Dev server settings (port 3000) and the Vitest settings for `npm test`. |
| `src/test/setup.js`, `src/**/*.test.js(x)` | Frontend tests (`npm test`, decision T1). Development only, never part of the build. |
| `src/config.js` | Settings from `frontend/.env`: backend address and company timezone. |
| `src/api/client.js` | One shared Axios instance: adds the login token to every call; on 401 clears it and returns to Sign in. |
| `src/api/tokenStorage.js` | Where the token is kept (tab session storage) and why. |
| `src/api/errors.js` | Turns the backend's error format into a readable sentence. |
| `src/api/auth.js`, `src/api/health.js` | Calls to the login and health endpoints. |
| `src/context/AuthContext.jsx` | Who is logged in: `login()`, `logout()`, `user`, `role`; reloads the user on refresh. |
| `src/context/NotificationContext.jsx` | Pop-up success/error messages: `useNotify().success('Saved')`. |
| `src/routes/navigation.js` | **One list** of every page, its menu label, icon and allowed roles. Menu and protection both use it. |
| `src/routes/AppRoutes.jsx`, `RequireAuth.jsx`, `RequireRole.jsx` | Page addresses; "must be logged in"; "must have an allowed role" (else **Not allowed**). |
| `src/layouts/MainLayout.jsx`, `Sidebar.jsx` | Top bar (name, role, Log out) and the role-based menu (collapses below 900px wide). |
| `src/pages/` | `LoginPage`, `NotAllowedPage`, `ComingSoonPage`, `NotFoundPage`; `users/` (Users page, create/edit form); `dev/ComponentGalleryPage` (development only). |
| `src/api/users.js` | Calls to the Admin-only user endpoints. |
| `src/api/categories.js` | Calls to the category endpoints, plus the "One-by-one" / "By quantity" labels. |
| `src/api/stockItems.js`, `src/pages/inventory/` | Inventory page (Admin and IT Manager): stock items with category, unit, reorder threshold and read-only quantity on hand; add/edit dialog whose category list shows only active "By quantity" categories; activate/deactivate with a confirm box. **Slice 4.3:** an orange **Low stock** badge next to "On hand" (`LowStockBadge.jsx`), a **Stock level** filter (All / Low stock) with Clear filters and "No matches", and the item name opens the **stock item page** `/inventory/:id` (`StockItemDetailPage.jsx`): quantity on hand, reorder threshold, stock level, category, unit, status, Edit and Activate / Deactivate (same boxes as the list), and the **Movement history** (date, type, +/- change, balance after, reference linking to the purchase, reason, saved at and by whom). Tests: `InventoryLowStock.test.jsx`, `StockItemDetailPage.test.jsx`. |
| `src/api/vendors.js`, `src/pages/vendors/` | Vendors page (Admin and IT Manager): list, search, status filter, add/edit dialog, activate/deactivate with a confirm box; vendor detail page `/vendors/:id` with Edit/Deactivate and the vendor's **Purchase history** (Slice 3.4, `VendorPurchaseHistory.jsx`): all its purchases, newest purchase date first, paged; a row opens the purchase. |
| `src/api/purchases.js`, `src/pages/purchases/` | Purchases page (Admin and IT Manager): list with search, status and vendor filters and status badges; **New purchase** / edit-draft form with an active-vendor picker, reference, date, notes and a lines list (each line "By quantity" with an active stock item, or "One-by-one" with an active one-by-one category and a description), quantity and unit cost in ₹, line totals and grand total; cancel a draft after a confirm box. Received/cancelled purchases open read-only. `purchaseForm.js` holds the form's checks and totals (tested in `purchaseForm.test.js` and `PurchaseFormDialog.test.jsx`). **Receive** (Slice 3.2): the inbox icon on a draft row, or **Receive…** in the draft form (save changes first), opens `ReceivePurchaseDialog`: received date, received quantity per line and one row per unit (serial number, model, name, brand, warranty expiry, location), with "copy unit 1 to all units", per-row errors and a confirm box; the success message lists the new asset IDs. A received purchase shows "Received N of M" and its asset IDs per line. By-quantity lines (Slice 3.3) show the item, unit and a received-quantity field, with "In stock now / after receiving"; the success message lists the stock added. `receiveForm.js` holds the checks (tested in `receiveForm.test.js` and `ReceivePurchaseDialog.test.jsx`). **History (Slice 3.4):** purchase-date range filter and Received column (`purchaseColumns.jsx`, shared with the vendor page); the purchase number or **View** opens the detail page `/purchases/:id` (`PurchaseDetailPage.jsx`): vendor and contact details, created / received by and when, lines with ordered and received quantities, unit cost, line totals and total, assets created (click an asset ID for its details) and stock movements. Received and cancelled purchases are read-only; a draft keeps Edit, Receive… and Cancel purchase. |
| `src/api/assets.js`, `src/pages/assets/` | **Assets page** (Slice 4.1, `AssetsPage.jsx`, Admin and IT Manager): the asset register with search by asset ID, serial number or name, **Category** (one-by-one categories), **Status** and **Location** (locations in use) filters, **Clear filters** and "No matches"; click a row (or Enter on it) to open the **asset page** `/assets/:assetId` (`AssetDetailPage.jsx`): Details (name, category, serial, model, brand, location, warranty, status, created by and when), Purchase (purchase and vendor links, invoice / reference, purchase date, cost; "No purchase" when entered by hand) and History (every audit log entry about the asset, newest first). `AssetDetailsDialog.jsx` (Slice 3.2) is the small details box opened from a received purchase's asset IDs. **Slice 4.2:** the asset page has **Edit** (`AssetEditDialog.jsx`: only the editable fields; asset ID, status, category and purchase facts shown read-only) and **Retire…** (`AssetRetireDialog.jsx`: confirm box that says it cannot be undone, required reason with a 500-character counter; greyed out unless Available or Damaged). A retired asset shows who retired it, when and why, and has no Edit or Retire. History shows each edit ("Location: A → B") and the retirement with its reason. Tests: `AssetsPage.test.jsx`, `AssetDetailPage.test.jsx`, `AssetEditDialog.test.jsx`, `AssetRetireDialog.test.jsx`. |
| `src/utils/money.js` | Rupee amounts: reads them as whole paise (no rounding errors) and shows them as ₹1,23,456.00. |
| `src/api/employees.js`, `src/pages/employees/` | Employees page (Admin and IT Manager): list, search, department/status filters, add/edit dialog with department suggestions, activate/deactivate with a confirm box that warns when a login will be deactivated too. |
| `src/components/EmployeePicker.jsx` | Search-as-you-type picker of active employees without a login; used in the Users dialogs (required for the Employee role). |
| `src/pages/categories/` | Categories page (Admin and IT Manager): list, search, filter, add/edit dialog, activate/deactivate with a confirm box. |
| `src/components/DataTable.jsx` | Search box, server-side paging and sorting, loading/empty/error states; optional `onRowClick` makes rows open something (mouse, Enter or Space). With `filtersActive` / `onClearFilters`, an empty result caused by search or filters says **No matches** and offers a button to clear them (used by Categories, Vendors, Employees and Inventory). |
| `src/components/FormField.jsx` | Text box with label, required `*` and error message. |
| `src/components/StatusBadge.jsx` | Coloured status: asset statuses (Available, Assigned, Under Maintenance, Damaged, Retired) record statuses (Active, Inactive) and purchase statuses (Draft, Received, Cancelled). |
| `src/components/ConfirmDialog.jsx` | "Are you sure?" box for consequential actions. |
| `src/components/LoadingState.jsx`, `EmptyState.jsx`, `ErrorMessage.jsx` | Loading spinner, "nothing here yet" and error box with "Try again". |
| `src/utils/dates.js` | `formatDateTime()` / `formatDate()`: show UTC times in the company timezone. `formatPlainDate()` shows a calendar date (e.g. a purchase date) as stored; `todayInCompanyTimezone()`. |
| `src/theme.js` | Shared colours and fonts (MUI theme). |

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `/health` shows `unreachable`, or `connection refused` on port 5433 | The dev database isn't running (it doesn't start with Windows). Run `scripts\dev-db start`. |
| `password authentication failed for user "itam_app"` or `database "itam_test" does not exist` | Run `scripts\dev-db init` (it adds anything missing). Check `.env` uses port `5433`, or copy `.env.example` to `.env` again. |
| `scripts\dev-db start` says `Server did not start` | Read the last lines of `.dev-db\postgres.log`. Port 5433 may be in use by the Docker database (`docker compose down`). |
| `failed to connect to the docker API` (option 2 only) | Docker Desktop isn't running. Start it and wait until it's ready. |
| `Port 3000 is in use` | Another `npm run dev` is still running; close it. |
| `pytest` exits with `TEST_DATABASE_URL is not set` | Add `TEST_DATABASE_URL` to `backend\.env`. |
| Server won't start: `jwt_secret_key ... Field required` or `at least 32 characters` | Add a `JWT_SECRET_KEY` to `backend\.env` (step 4.4). |
| `relation "users" does not exist` | Run the migrations: `.venv\Scripts\alembic upgrade head`. |
| Swagger says `401 invalid_token` | The token expired or was pasted with quotes. Log in again and paste only the token. |
| Users page: `cannot_change_self` | You can't deactivate yourself or remove your own Admin role. Ask another Admin. |
| Users page: `last_admin` | Make another user an Admin before demoting or deactivating this one. |
| Categories: `category_name_taken` | A category with that name already exists (upper/lower case is ignored, inactive ones count too). Use another name, or activate the existing one. |
| Categories: `tracking_type_locked` | Items or assets already use this category, so it cannot switch between one-by-one and by quantity (from Slice 2.4 / 3.2 onward). |
| Categories, Vendors, Employees, Inventory, Purchases: a filter shows fewer (or no) rows than expected ("No matches") | The **Tracking** and **Status** filters combine: a category must match both (e.g. Inactive + By quantity shows only inactive by-quantity categories). The same applies to every list with more than one filter (e.g. Department + Status on Employees, Category + Status on Inventory, Status + Vendor + purchase dates on Purchases). Click **Clear filters**, then set one filter at a time. |
| Categories: there is no Delete | On purpose (BR-12). Deactivate the category instead; it stays visible but cannot be chosen for new records. |
| Inventory: `category_not_bulk` | That category is tracked one by one (e.g. laptops). Stock items need a "By quantity" category. |
| Inventory: `category_inactive` / empty category list | Only active "By quantity" categories can be chosen. Add or activate one on the Categories page first. |
| Inventory: `stock_item_name_taken` | That category already has an item with this name (upper/lower case is ignored). |
| Inventory: `stock_not_zero` / `unit_locked` | An item with stock can't be deactivated (issue or adjust it to 0 first, Slice 4.4), and once it has any stock movement its unit can't change, even at 0. |
| Inventory: an item at 0 is not marked "Low stock" | It is **inactive**: inactive items are never flagged (G1), because they cannot be restocked. Active items are flagged when on hand is **at or below** the reorder threshold (B37). |
| Inventory: "Low stock" on an item with exactly the threshold | Correct: "at or below" the threshold counts (B37). A threshold of 0 warns only when stock reaches 0. |
| Stock item page: the movement history is not in date order | It is in the order the movements were **saved**, newest first (G2), so "Balance after" reads as a running balance. A receipt entered late shows its earlier business date in the Date column. |
| Stock item page: "Stock item not found" | The id in the address does not exist. Open the item from the Inventory list instead. |
| Inventory: quantity on hand can't be edited | On purpose: it changes only through receiving (3.3), issue/adjust (4.4) and opening stock (4.5). |
| Categories: `tracking_type_locked` now | Since Slice 2.4, a category with stock items can't switch between one-by-one and by quantity. |
| Vendors: `vendor_name_taken` | A vendor with that name already exists (upper/lower case is ignored, inactive ones count too). Use another name, or activate the existing vendor. |
| Vendors: there is no Delete | On purpose (BR-12, VEN-05). Deactivate the vendor instead: it stays visible, but new purchases can't use it (from Slice 3.1). |
| Users: `employee_link_required` | An Employee login must be linked to an employee record. Pick one in the dialog (add the employee on the Employees page first). |
| Users: `employee_has_login` / `employee_inactive` | That employee already has a login, or is deactivated. Pick another, or activate the employee first. |
| Users page shows **Needs employee link** | An Employee login created before Slice 2.2 without an employee record (R3). It still works; edit the user and pick the employee. |
| Employees: `employee_code_taken` / `work_email_taken` | Another employee already has that employee ID or work email (upper/lower case is ignored). |
| Employees: `cannot_change_self` | The employee record is linked to your own login, and deactivating it would lock you out. Ask another Admin. |
| Purchases: `vendor_inactive` / `stock_item_inactive` / `category_inactive` | Only active vendors, stock items and categories can be chosen. When editing a draft, things already on it keep working even if deactivated since; only new choices are checked. |
| Purchases: `category_not_serialized` | A "One-by-one" line needs a category tracked one by one (e.g. laptops). For mice, cables etc. use a "By quantity" line with the stock item. |
| Purchases: `purchase_reference_taken` | This vendor already has a draft or received purchase with that invoice / reference number (upper/lower case ignored). A cancelled purchase does not count. |
| Purchases: `purchase_date_in_future` | The purchase date must be today or earlier (company timezone). |
| Purchases: `invalid_date_range` | The "from" purchase date is after the "to" date. Swap them or clear one (**Clear filters**). |
| Purchases list / vendor page: `vendor_not_found` | The vendor id in the address does not exist (inactive vendors still show their history). |
| Purchase detail: "Received by: Not recorded" | A purchase received before migration 0011 that had no `purchase.received` audit row to copy from. Nothing else is affected. |
| Purchase detail: database error about `received_by_user_id` | Your database is behind: run `alembic upgrade head` (migration 0011, Slice 3.4). |
| Purchases: `purchase_not_draft` | Only drafts can be edited or cancelled. Received and cancelled purchases are final (P6). |
| Purchases: there is no Delete | On purpose (BR-12). Cancel the draft instead; it stays in the list as **Cancelled** and changes no stock. |
| Categories: `tracking_type_locked` on a one-by-one category | Since Slice 3.1, a category used on any purchase line can't switch tracking type either; since Slice 3.2, nor can a category with any asset (even a retired one). |
| Receive: `stock_item_inactive` | A "By quantity" line's stock item was deactivated after the draft was saved. Reactivate it on the Inventory page, or receive 0 for that line. Nothing was saved. |
| Receive fails with a database error about `stock_movements` | Your database is behind: run `alembic upgrade head` (migration 0010, Slice 3.3). |
| Receive: `serial_number_taken` / `serial_number_duplicate` | Serial numbers are unique across all assets, ignoring upper/lower case. `taken`: an existing asset already has it. `duplicate`: it is typed twice in this receipt. Nothing was saved; fix the marked row and receive again. |
| Receive: `received_quantity_too_high` / `nothing_received` | Each line takes 0 up to the ordered quantity (fewer closes the line; the rest is never received later). At least one unit must arrive in the whole receipt. |
| Receive: `received_date_before_purchase` / `received_date_in_future` | The received date must be between the purchase date and today (company timezone). |
| Receive: `purchase_not_draft` | Only a draft can be received, once. Received purchases are final (P6): fix mistakes by retiring the asset (Slice 4.2). |
| Login says "Incorrect email or password" and nobody knows the dev password | The app has no password reset (R2). On a **development** machine (with `APP_ENV=development` in `backend\.env`) run `.venv\Scripts\python -m app.scripts.reset_password --email <the login's email>` from `backend` and type a new password (12+ characters) twice. A deactivated login must still be activated on the Users page. |
| `reset_password` says "for development only (APP_ENV is …)" | On purpose (D8): it runs only when `APP_ENV=development` is set explicitly. Add that line to `backend\.env` on your own machine. Never set it on a server. |
| `ADMIN_PASSWORD` in `backend\.env` doesn't work | It is only read by `create_admin` when the **first** Admin is made; changing it later changes nothing. Use `reset_password` instead. |
| Assets: a search finds nothing for a model, brand or location | On purpose (Slice 4.1): the search box matches the asset ID, serial number and name only. Use the **Location** filter for locations; sort by **Model** to group models. |
| Assets: the **Location** filter misses an asset | The filter matches the **whole** location, ignoring upper/lower case: "Floor 2" does not match "Bangalore Floor 2". Locations are typed text (Q1), so spellings that differ by more than case ("Blr Floor 2") are separate entries. |
| Assets: there is no Employee filter | Assignments arrive in Slice 5.1; the employee filter is added then (owner's answer A1). |
| Assets: `category_not_found` | The `category_id` in the request does not exist (inactive categories still work). |
| Asset page: "Asset not found" | The asset ID or id in the address does not exist. Check the spelling (AST- followed by 6 digits). |
| Asset page: History shows only "Created" | Nobody has edited or retired it yet. Edits and retiring (4.2) add "Edited" / "Retired" entries; assignments (5.x) and maintenance (6.x) add theirs when they are built. |
| Asset page: **Retire…** is greyed out | Only **Available** or **Damaged** assets can be retired (A3). Return an Assigned asset first (Phase 5); finish a repair first (Phase 6). The server answers `asset_not_retirable` too. |
| Asset page: no Edit or Retire buttons | The asset is **Retired**: retiring is final and a retired asset is read-only (A3). |
| Edit asset: there is no field for category, cost or purchase date | On purpose (A2): they come from the invoice and stay locked. Status changes only through actions such as Retire. Sent through the API anyway: `validation_error`. |
| Edit asset: `serial_number_taken` | Another asset already uses that serial number (upper/lower case is ignored). Changing only the case of the asset's own serial is fine. |
| Retire: `invalid_retire_reason` | The reason is required (spaces alone do not count) and can be at most 500 characters. |
| Asset page or migration error about `retired_at` / `retire_reason` | Your database is behind: run `alembic upgrade head` (migration 0012, Slice 4.2). |
| `create_user` says `--employee-code is required` | Employee logins need an employee record: add one on the Employees page, then pass its ID. |

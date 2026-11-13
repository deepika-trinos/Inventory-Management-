# Decisions Log — IT Asset & Inventory Management System

- **Source of truth:** PRD v1.0 (`IT_Asset_Inventory_Management_PRD_v1.pdf`)
- **Build plan:** v1.2 (`IT_Asset_Inventory_Build_Plan_Phases.docx`)
- **Recorded in:** Phase 1, Slice 1.1 (Approve the plan)
- **Date of decisions:** 2026-11-10
- **Decided by:** Project owner
- **Plan approval status:** ✅ Approved by the owner on 2026-11-10

> Rule: the team does not invent business rules. Anything the owner has not decided is marked **OPEN** together with the slice it blocks.

---

## 1. Requirement coverage check

All **82** PRD requirement IDs appear in at least one slice of build plan v1.2. **None are missing.**

| Group | IDs | Slices |
|---|---|---|
| AUTH | 01–06 | 1.3 (01–04, 06), 1.5 (01–02), 1.6 (05) |
| DASH | 01–05 | 7.1 |
| AST | 01–07 | 3.2 (01, 06), 2.1 / 4.1 (02), 4.1 (03, 05), 4.2 (04, 07), 4.5 (01) |
| INV | 01–07 | 2.4 / 4.5 (01), 4.3 (02, 05, 06), 3.3 (03, 05), 4.4 (04, 07) |
| VEN | 01–05 | 2.3 (01–03, 05), 3.4 (04) |
| PUR | 01–09 | 3.1 (01–04, 08), 3.2 (05, 06), 3.3 (07), 3.4 (09) |
| EMP | 01–05 | 2.2 (01–03), 5.3 (04), 5.1 (05) |
| ASN | 01–08 | 5.1 (01–04), 5.2 (05, 06), 5.3 (07, 08) |
| MNT | 01–08 | 6.1 (01–03), 6.2 (04–07), 6.3 (07), 6.4 (08) |
| REP | 01–08 | 7.2 (01, 02, 07, 08), 7.3 (03, 04, 08), 7.4 (05, 06, 08) |
| BR | 01–14 | 3.2 (01, 07, 08), 5.1 (02, 03, 05, 11), 5.2 (04), 6.2 (05), 3.1 (06), 3.3 / 4.4 (09), 4.4 (10), 2.2 / 2.3 (12), 1.4 / 4.2 / 8.1 (13), 1.3 / 8.2 (14) |

**Smaller gaps found (not missing IDs; to keep in mind when building those slices):**

1. **BR-13 (traceability):** Slices 4.4 (stock issue/adjust), 5.2 (return) and 6.2 (maintenance status changes) don't mention writing an audit log entry. BR-13 requires it. Slice 8.1's done-check expects returns and stock changes in the audit log.
2. **BR-12 (deactivate, don't delete):** Listed for employees (2.2) and vendors (2.3), but not for asset categories (2.1) or bulk stock items (2.4). Both of those are referenced by other records. *Resolved: categories in Slice 2.1 (B13), stock items in Slice 2.4 (B38).*
3. **PRD 17.2 "Maintenance ownership"** (separate technician role) had no question in the plan. It is now recorded as Q13 below.

---

## 2. Business decisions ("Before you start" questions + PRD 17.2)

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| Q1 | Is an asset's location typed in, or picked from a list of offices/rooms? | **Typed in** as simple free text for now. | 2026-11-10 | 3.2, 4.1, 4.5 | Decided |
| Q2 | Can a purchase be received in parts (e.g. 3 of 5 laptops now, 2 later)? | **No.** One receipt per purchase line. | 2026-11-10 | 3.1, 3.2, 3.3 | Decided |
| Q3 | Does the system create asset IDs, or do people type them? | **System creates them** in sequence: AST-000001, AST-000002, … | 2026-11-10 | 3.2, 4.5 | Decided |
| Q4 | How do we enter equipment the company already owns? | **Manual asset entry** for one-by-one items, plus a **one-time opening stock** entry for bulk items. | 2026-11-10 | 4.5, 8.5 | Decided |
| Q5 | Is the condition check (inspection) done on the same form as the return? | **Yes, same form.** | 2026-11-10 | 5.2 | Decided |
| Q6 | Does every employee get a login, and who creates it? | **Admin creates logins** and links each one to an employee record. (Not every employee must have a login.) | 2026-11-10 | 1.3, 1.6, 2.2 | Decided |
| Q7 | Do stock adjustments need approval, or is a reason + audit record enough? | **Mandatory reason + audit record.** No approval step in v1. | 2026-11-10 | 4.4 | Decided |
| Q8 | Is CSV/PDF export of reports needed in the first release? | **Postpone.** Reports are on screen only in v1. | 2026-11-10 | 7.4 (Phase 7) | Decided |
| Q9 | When does an asset become Under Maintenance: when reported, or when work starts? | **When work starts:** the IT Manager sets the request to In Progress. | 2026-11-10 | 6.1, 6.2 | Decided |
| Q10 | Should maintenance requests have a priority (Low/Medium/High)? | **Yes, optional** field, set by the IT Manager. | 2026-11-10 | 6.1, 6.2 | Decided |
| Q11 | Which timezone should dates be shown in? | **Store in UTC; display in Asia/Kolkata.** The timezone is a configuration setting. | 2026-11-10 | 1.3, 8.2 | Decided |
| Q12 | Which hosting, domain and backup frequency for go-live? | **Backups at least daily** (decided). Hosting provider and domain to be **decided before Phase 8**. | 2026-11-10 | 8.5 | **OPEN** (hosting + domain only), blocks **Slice 8.5** |
| Q13 | (PRD 17.2, not in the plan) Is a separate maintenance technician role needed later? | **Not in the MVP.** IT Manager owns maintenance. Revisit after go-live; any new role would be a future scope change. | 2026-11-10 | Phase 6 (6.1–6.3); future | Decided for MVP |

**PRD 17.2 "Warranty reminders":** The PRD already decides this: warranty-expiry reporting is in the MVP (Slice 7.2) and automated notifications are future scope. No question was needed.

---

## 3. Approved helper tools and server libraries

None of these change the main stack fixed by the PRD (React.js, JavaScript, Python, FastAPI, PostgreSQL, SQLAlchemy, Pydantic, Alembic, JWT).

| Tool / library | What it does (plain words) | Decision | Date | First used in |
|---|---|---|---|---|
| Vite | Runs the React app during development and builds it for go-live | ✅ Approved | 2026-11-10 | 1.2 |
| React Router | Separate pages with their own web addresses; blocks pages by role | ✅ Approved | 2026-11-10 | 1.5 |
| Axios | Sends requests from the screens to the server; attaches the login token | ✅ Approved | 2026-11-10 | 1.5 |
| MUI (Material UI) | Ready-made buttons, tables, forms and dialogs | ✅ Approved | 2026-11-10 | 1.5 |
| pytest | Runs the automated tests | ✅ Approved | 2026-11-10 | 1.2 |
| uvicorn | The web server program that runs the FastAPI app | ✅ Approved | 2026-11-10 | 1.2 |
| psycopg (v3) | Driver that connects SQLAlchemy to PostgreSQL | ✅ Approved | 2026-11-10 | 1.2 |
| pwdlib + Argon2 | Password hashing (stores a one-way scrambled fingerprint, never the password) | ✅ Approved (passlib + bcrypt **not** chosen) | 2026-11-10 | 1.3 |
| PyJWT | Creates and checks JWT login tokens | ✅ Approved (python-jose **not** chosen) | 2026-11-10 | 1.3 |
| httpx (testing only) | Required by FastAPI's test client to call the API inside tests | ✅ Approved with the Slice 1.2 sign-off | 2026-11-10 | 1.2 |
| Vitest + React Testing Library (testing only) | Automatic tests for the screens (`npm test`); development only, never shipped to users | ✅ Approved (T1) | 2026-11-12 | 3.1 |

**T1 as installed in Slice 3.1** (dev-only `devDependencies`, pinned to exact versions in
`frontend/package.json`; B54, ✅ signed off with Slice 3.1 on 2026-11-13):

| Package | Exact version | Why |
|---|---|---|
| `vitest` | 5.1.0 | The test runner (`npm test` = `vitest run`) |
| `@testing-library/react` | 16.3.3 | Draws a screen in a test and finds things on it the way a user would |
| `@testing-library/dom` | 10.4.2 | Required companion of `@testing-library/react` (it must be installed alongside) |
| `jsdom` | 31.0.0 | The pretend browser page the tests run in (Vitest's `environment: 'jsdom'`) |

Not installed (not needed yet): `@testing-library/jest-dom` and `@testing-library/user-event`.

---

## 4. Phase 1 order fixes

| Fix | Change | Decision | Date | Affects slice(s) |
|---|---|---|---|---|
| a | The first Admin account is created by a **seed script** (a one-time program that adds starting data) in **Slice 1.3**, not in 1.6. The Admin's login details come from environment settings, never from the code. | ✅ Confirmed | 2026-11-10 | 1.3, 1.6 |
| b | A user's link to an employee record is **optional in Phase 1**. After Employees are built in **Slice 2.2**, the link becomes **required for Employee-role users**. | ✅ Confirmed | 2026-11-10 | 1.3, 1.6, 2.2 |
| c | Slice 1.4's "role change writes an audit row" check is proved with an **automated test**. It is then **re-checked through the real role-change feature in Slice 1.6** (added to 1.6's done-check). | ✅ Confirmed | 2026-11-10 | 1.4, 1.6 |

---

## 5. OPEN items

| Item | What is still undecided | Blocks | Decide by |
|---|---|---|---|
| Q12 | Hosting provider and domain | Slice 8.5 | Before Phase 8 starts |
| R2 | **Temporary passwords:** must a user change the temporary password at first login? Is a "forgot / reset password" feature needed (the PRD has none)? Today the Admin hands over the password and the user keeps it. | Nothing in Phase 2; affects security review (Slice 8.3) | Before Slice 8.3 |

**Slice 3.1 decisions B42–B54 are signed off (section 14). Slice 3.2 decisions B55–B66 are pending the owner's sign-off (section 15).** R1 is decided (see section 8). R3 is decided (see section 10). T1 is approved (see section 3). P1–P8 are decided (see section 13). Nothing OPEN blocks Phase 3.**

---

## 6. Slice 1.1 sign-off

- [x] Every PRD requirement ID is mapped to a slice
- [x] Questions 1–6 and 11 answered (needed for Phases 1–2)
- [x] Helper tools and server libraries approved
- [x] Phase 1 order fixes confirmed
- [x] No OPEN item blocks Slice 1.2
- [x] Owner says **"approved"**. Date: 2026-11-10

**Slice 1.1 is complete. Next: Slice 1.2 (Project setup).**

---

## 7. Decisions made while building (approved with each slice's sign-off)

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| B1 | **Local development database** is the project's own PostgreSQL server (`scripts\dev-db`, port 5433, data in `.dev-db/`, never committed). Docker (`docker-compose.yml`) kept as an alternative. | The installed PostgreSQL's `postgres` password is unknown; this needs no password, no admin rights, and leaves the existing server untouched. | 2026-11-11 | 1.2 |
| B2 | **Minimum password length: 12 characters** (setting `PASSWORD_MIN_LENGTH`). | The PRD sets no rule; 12 is a common secure minimum. Can be changed in settings. | 2026-11-11 | 1.3 |
| B3 | **Deactivated account at login:** after a *correct* password, the user sees "account deactivated" (403). A wrong password always gets the same generic error. | Clear message for real users without revealing which emails exist. | 2026-11-11 | 1.3 |
| B4 | **`create_user` script** for development-only test accounts (refuses to run in production). | Needed to test IT Manager / Employee roles before user management exists (Slice 1.6). | 2026-11-11 | 1.3 |
| B5 | **Email check** is a simple format check (something@something.something), emails stored in lower case. | Strict validation would need an extra, unapproved library. | 2026-11-11 | 1.3 |
| B6 | **Login tokens expire after 30 minutes** (setting `ACCESS_TOKEN_EXPIRE_MINUTES`); logout = the frontend deletes its token. | Short-lived tokens limit damage from a copied token; deactivation takes effect on the next request anyway. | 2026-11-11 | 1.3 |

---

## 8. Decisions in Slices 1.5–1.6 (pending the owner's sign-off of those slices)

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| R1 ✅ | **User-management safety rules** (from the Slice 1.6 brief): an Admin cannot deactivate themselves or remove their own Admin role; the last active Admin cannot be deactivated or demoted; duplicate emails (any case) are blocked. | Prevents locking everyone out of user management. | 2026-11-11 | 1.6 |
| B7 | **Login token kept in the browser tab's sessionStorage.** Survives refresh; cleared when the tab closes; each new tab logs in separately. A cookie JavaScript cannot read (httpOnly) is the stronger option to consider in Slice 8.3. | Simplest safe choice without backend changes. | 2026-11-11 | 1.5 |
| B8 | **`@mui/icons-material`** (MUI's own icon set) added, treated as part of the approved MUI. | Menu and button icons. | 2026-11-11 | 1.5 |
| B9 | **Frontend timezone** set by `VITE_APP_TIMEZONE` (must match the backend's `APP_TIMEZONE`). | Dates shown in company time (Q11). | 2026-11-11 | 1.5 |
| B10 | **Session re-checked on every page change** (`/auth/me`), so a deactivated user is signed out on their next click and a changed role updates the menu immediately. | Makes "logged out on the next request" true even on pages that call no API yet. | 2026-11-11 | 1.6 |
| B11 | **Every user change is audited**, including accounts made by the seed scripts (recorded as system actions with no actor). | BR-13: complete history of who created which account. | 2026-11-11 | 1.6 |
| B12 | **Employee link is API-only for now:** the Users screen has no employee picker until the Employees module exists (Slice 2.2). *Resolved in Slice 2.2: the Users create/edit and role dialogs now have an employee picker (active employees without a login).* | No employee list to pick from yet. | 2026-11-11 | 1.6 |

---

## 9. Decisions in Slice 2.1 (✅ Slice 2.1 signed off by the owner, 2026-11-12)

✅ = approved by the owner on 2026-11-12 (B15, B16, as written). The others were approved with the Slice 2.1 sign-off.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| B13 | **BR-12 applies to asset categories** (from the Slice 2.1 brief; closes gap 2 for categories): no delete endpoint or function; categories are deactivated instead. A deactivated category stays readable (list, get one) and can be activated again, but cannot be chosen for new records: helper `ensure_category_selectable()` (error `category_inactive`), first called in Slice 2.4. | Categories are referenced by stock items and assets. | 2026-11-12 | 2.1 (2.4+) |
| B14 | **Tracking type locks once a category is used** (from the Slice 2.1 brief): changing between one-by-one (`serialized`) and by quantity (`bulk`) is refused (`tracking_type_locked`) once any stock item or asset uses the category. The guard exists now but cannot fire until Slice 2.4 (stock items) / 3.2 (assets) add their checks to `_category_in_use()`. | PRD 9.2: the same units must never be counted in both models. | 2026-11-12 | 2.1 (2.4, 3.2) |
| B15 ✅ | **Category names:** unique ignoring upper/lower case, **including inactive categories** (so an old name is reused by activating it, not by creating a twin). Leading/trailing spaces are removed. Limits: name 100 characters, description 500 (optional). | One category per name avoids two "Laptops" in pickers and reports. Limits are technical, not from the PRD. | 2026-11-12 | 2.1 |
| B16 ✅ | **Inactive categories can still be edited** (name, description, tracking type, subject to B14). Activating an active category, or deactivating an inactive one, changes nothing and writes no audit row. | Lets the record be corrected without reactivating it; same "no change, no audit row" pattern as users (B11). | 2026-11-12 | 2.1 |
| B17 | **Category audit actions:** `category.created`, `category.updated`, `category.activated`, `category.deactivated`, each with before/after name, description, tracking type and status (BR-13, following B11). | Complete history of master-data changes. | 2026-11-12 | 2.1 |
| B18 | **Employees cannot call any category endpoint** (403, from the Slice 2.1 brief). When Employee screens later need a category name (e.g. My Assets, Slice 6.4), it will come inside the asset data, not from `/categories`. | Categories are maintained by Admin and IT Manager only. | 2026-11-12 | 2.1 (6.4) |
| B19 | **Sidebar:** Categories is a plain menu item right after Inventory (Admin and IT Manager); no menu groups. | Chosen by the owner on 2026-11-12. | 2026-11-12 | 2.1 |
| B20 | **`StatusBadge` also shows record statuses** Active (green) and Inactive (grey, outlined), for categories and later employees, vendors and stock items. Asset statuses are unchanged. | One consistent status label across the app. | 2026-11-12 | 2.1 |

---

## 10. Decisions in Slice 2.2 (✅ Slice 2.2 signed off by the owner, 2026-11-12)

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| R3 ✅ | **Employee-role users created before Slice 2.2 without an employee link keep logging in** until an Admin links them. The API marks them `needs_employee_link: true` and the Users page shows **Needs employee link**. From now on, every new Employee login, every edit and every role change to Employee must include a link. | Owner's answer (option 1), 2026-11-12. Nobody is locked out. | 2026-11-12 | 2.2 |
| B21 | **Deactivating an employee also deactivates the linked login**, in the same transaction, with its own `user.deactivated` audit row (`reason: employee_deactivated`). Activating the employee does **not** reactivate the login; the Admin does that on the Users page. The R1 rules still apply: you cannot deactivate the employee record linked to your own login (`cannot_change_self`), and the last active Admin's record cannot be deactivated (`last_admin`). | Owner's answer (option 1), 2026-11-12: someone who left must not keep signing in. | 2026-11-12 | 2.2 |
| B22 | **Contact details = one optional phone number** (besides work email), up to 30 characters: digits, spaces and `+ ( ) . / -`. Its format is not checked further. | Owner's answer (option 1), 2026-11-12. EMP-02 does not list the fields. | 2026-11-12 | 2.2 |
| B23 | **Department is typed in**, with suggestions of departments already used (`GET /employees/departments`, one spelling per department ignoring case). The department filter is an exact match ignoring case. Designation is also free text. | Owner's answer (option 1), 2026-11-12; same approach as location (Q1). | 2026-11-12 | 2.2 |
| B24 | **Employee ID (`employee_code`) is unique ignoring upper/lower case** (e.g. `EMP-001` = `emp-001`), stored as typed with spaces trimmed. **Work email** is optional, stored in lower case (B5) and unique ignoring case; many employees may have none. Limits: ID 30, name 150, department/designation 100. | Avoids look-alike duplicates. Limits are technical, not from the PRD. | 2026-11-12 | 2.2 |
| B25 | **Employee link rules for logins:** only an **active** employee **without another login** can be linked (`employee_inactive`, `employee_has_login`). The link is required only for the Employee role; Admin and IT Manager logins may be linked or not. An Employee login's link can be changed to another employee but not removed. A role change away from Employee keeps the link. | Order fix b, and the Slice 2.2 brief (picker shows only active employees without a login). | 2026-11-12 | 2.2 |
| B26 | **New audit actions:** `employee.created`, `employee.updated`, `employee.activated`, `employee.deactivated`, and `user.employee_link_changed` (before/after employee id and code), written whenever an existing login's link changes (edit or role change). A new login's link is recorded in `user.created`. | BR-13, following B11. | 2026-11-12 | 2.2 |
| B27 | **Employee search** (EMP-03) matches part of the employee ID, name or department, ignoring case. Indexes on lower(employee ID), lower(name) and lower(department) speed up exact and sorted lookups; "contains" searches still scan the table, which is fine at company size (revisit if employees grow into the tens of thousands). | Simple and needs no extra database extension. | 2026-11-12 | 2.2 |
| B28 | **Inactive employees can still be edited** and stay readable; repeating activate/deactivate changes nothing and writes no audit row. EMP-05 (no new assignments to inactive employees) is enforced in Phase 5. | Same pattern as categories (B16) and users. | 2026-11-12 | 2.2 (5.1) |
| B29 | **Dev script `create_user`** needs `--employee-code` for the Employee role. Test fixtures create a linked employee automatically for Employee-role test users. | Order fix b applies to scripts too. | 2026-11-12 | 2.2 |

---

## 11. Decisions in Slice 2.3 (✅ Slice 2.3 signed off by the owner, 2026-11-12)

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| B30 | **Vendor names are unique ignoring upper/lower case**, active or inactive (`vendor_name_taken`). Spaces at the ends are removed. | Owner's answer, 2026-11-12. Avoids look-alike vendors in the Slice 3.1 purchase picker; same rule as categories (B15). | 2026-11-12 | 2.3 |
| B31 | **Only the vendor name is required.** Contact person, email, phone and address are optional ("where available", VEN-02). Email is stored in lower case (B5), checked for format, and **may repeat** across vendors. Phone uses the employee phone check (B22). Limits: name and contact person 150, address 500 characters. | Owner's answers, 2026-11-12. | 2026-11-12 | 2.3 |
| B32 | **Vendor detail page at `/vendors/:id`** with Edit, Activate/Deactivate and a **Purchase history** section that is a placeholder until Slice 3.4 (VEN-04). The vendor name in the list links to it. | Owner's answer, 2026-11-12. Gives Slice 3.4 a page with its own address to fill in. | 2026-11-12 | 2.3 (3.4) |
| B33 | **Inactive vendors** stay readable and editable; only new purchases are blocked, through `ensure_vendor_active()` (`vendor_inactive`), which Slice 3.1 calls. Repeating activate/deactivate changes nothing and writes no audit row. | BR-12 / VEN-05; same pattern as categories (B13, B16) and employees (B28). | 2026-11-12 | 2.3 (3.1) |
| B34 | **Vendor search** (VEN-03) matches part of the name, contact person, email or phone, ignoring case; the only filter is status. Audit actions: `vendor.created`, `vendor.updated`, `vendor.activated`, `vendor.deactivated` (before/after of every field). | VEN-03 and BR-13 (B11). | 2026-11-12 | 2.3 |

---

## 12. Decisions in Slice 2.4 (✅ Slice 2.4 signed off by the owner, 2026-11-12; B35–B41 approved)

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| B35 | **Unit of measure is a fixed list:** pieces, boxes, packs, pairs, sets, rolls, metres (database check constraint). Adding a unit later is a small migration. | Owner's answer, 2026-11-12. Keeps reports consistent (no "pcs" vs "pieces"). | 2026-11-12 | 2.4 |
| B36 | **The unit locks once the item has stock** (`unit_locked`). The guard exists now but cannot fire until stock arrives: Slice 3.3 must also count "any stock movement exists" in `_has_stock_history()`. Name, category and threshold stay editable. | Owner's answer, 2026-11-12: 10 boxes must not silently become 10 pieces. | 2026-11-12 | 2.4 (3.3) |
| B37 | **Reorder threshold is required**, a whole number from 0 to 1,000,000; the form starts at 0. Low stock (Slice 4.3, INV-06) = quantity at or below the threshold, so 0 warns only when stock runs out. | Owner's answer, 2026-11-12. The upper limit is technical. | 2026-11-12 | 2.4 (4.3) |
| B38 | **A stock item can only be deactivated at zero stock** (`stock_not_zero`); issue or adjust it to 0 first (Slice 4.4). Never deleted (BR-12, closes gap 2 for stock items). Activating does not re-check the category. | Owner's answer, 2026-11-12. | 2026-11-12 | 2.4 (4.4) |
| B39 | **PRD 9.2 inventory model: a stored balance plus movement history.** `quantity_on_hand` (>= 0, database check, INV-07) is the balance; it is read-only in the API (sending it is a validation error) and starts at 0. From Slice 3.3, every change writes a stock movement row and updates the balance **in the same transaction**, so the two always match; serialized items never become stock items (category must be "bulk"). | Answers the PRD 9.2 question (balance vs derived). A stored balance is fast to read for lists and low-stock checks; one transaction keeps it consistent with the history. | 2026-11-12 | 2.4 (3.3, 4.4, 4.5) |
| B40 | **Stock item category rules:** on create, and whenever the category is changed, it must be an **active** category tracked **by quantity** (`category_not_bulk`, `category_inactive`). An item keeps working if its category is deactivated later. Stock items (active or inactive) now count as "category in use" for the tracking-type lock (B14). | Brief's key rule; PRD 9.2. | 2026-11-12 | 2.4 |
| B41 | **Stock item names are unique within their category**, ignoring case (the same name may exist in another category). Name limit 150 characters. Search matches part of the name; filters: category and status. API path `/api/v1/stock-items` (module `inventory`). Helper `ensure_stock_item_usable()` (`stock_item_inactive`) for Slices 3.1, 4.4 and 4.5. Audit actions `stock_item.created/updated/activated/deactivated`. | Brief; same patterns as categories and vendors. | 2026-11-12 | 2.4 |

---

## 13. Phase 2 sign-off and Phase 3 decisions

**✅ Phase 2 (Master data) signed off by the owner on 2026-11-12** (Slices 2.1–2.4, decisions B13–B41).

Phase 3 questions from `Phase2_WrapUp.md`, **all accepted as proposed** by the owner on 2026-11-12:

| # | Decision | Affects slice(s) |
|---|---|---|
| P1 ✅ | **Purchase lines:** a bulk line points to an existing **stock item**; a serialized line points to a **category plus a free-text description** (e.g. "Laptops: Dell Latitude 5440"). | 3.1 |
| P2 ✅ | **Money:** Indian rupees (INR) only; unit cost with **2 decimal places**; a cost of **0 is allowed** (free or replacement items). No tax (excluded by the PRD). | 3.1 |
| P3 ✅ | **Invoice / reference number:** **required**, **unique per vendor** ignoring case. The purchase date **cannot be in the future**. | 3.1 |
| P4 ✅ | **Short deliveries** (with Q2, one receipt per line): the received quantity may be **lower** than ordered, **never higher**; the line is then closed. | 3.2, 3.3 |
| P5 ✅ | **Receiving one-by-one items:** **serial number and model required**; brand, warranty expiry and location (typed, Q1) optional. Serial numbers **unique across all assets**, ignoring case (AST-06). | 3.2 |
| P6 ✅ | **Who:** Admin and IT Manager may create, receive and cancel purchases. A **received purchase is final**: mistakes are corrected by a stock adjustment (4.4) or by retiring the asset (4.2). | 3.1–3.3 |
| P7 ✅ | **Stock movement types:** `receipt`, `issue`, `adjustment_in`, `adjustment_out`, `opening`. | 3.3, 4.4, 4.5 |
| P8 ✅ | **Vendors are never deleted** (BR-12), even ones without purchases. No change. | — |

---

## 14. Decisions in Slice 3.1 (✅ Slice 3.1 signed off by the owner, 2026-11-13; B42–B54 approved)

B42, B43, B45 and B46 are the owner's answers given while building (2026-11-12). The others are
technical or follow from P1–P6; all were **approved with the Slice 3.1 sign-off** (2026-11-13).

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| B42 | **System purchase number PUR-000001, PUR-000002, …** (owner's answer). Made by the database sequence `purchase_number_seq` when the purchase is saved; read-only; shown in lists, searchable, and recorded in the audit log. A save that fails after the number was taken leaves a gap (numbers are never reused). The vendor's invoice / reference number is kept separately. | Same style as asset IDs (Q3); gives every purchase an ID even when two vendors use the same invoice number. | 2026-11-12 | 3.1 |
| B43 | **A cancelled purchase frees its invoice / reference number** (owner's answer): the P3 rule "unique per vendor, ignoring case" applies to draft and received purchases only (partial unique index). Spaces at the ends are removed. | A draft cancelled by mistake can be entered again. | 2026-11-12 | 3.1 |
| B44 | **Technical limits:** reference 100 characters, notes 2,000, line description 200; quantity a whole number 1–100,000; unit cost 0 to 9,999,999,999.99 (NUMERIC 12,2); at most 100 lines per purchase. The API sends money as text with 2 decimals (`"1250.00"`) so nothing is rounded; it accepts a number or text. | Limits are technical, not from the PRD. | 2026-11-12 | 3.1 |
| B45 | **Editing a draft checks only what changed** (owner's answer): the vendor is checked for being active only when it is changed; a line's stock item or category only when it was not already on the draft. Sending `lines` replaces all the draft's lines. Cancelling is always allowed, even if the vendor or items were deactivated since. **Whether receiving (3.2 / 3.3) re-checks them is for those slices to confirm.** | Matches the B33 note "checked when a purchase is created or its vendor is changed"; a deactivation never traps an existing draft. | 2026-11-12 | 3.1 (3.2, 3.3) |
| B46 | **Purchase lines lock a category's tracking type** (owner's answer; extends B14): a one-by-one category used on any purchase line (any status, cancelled too) can no longer switch to "by quantity" (`tracking_type_locked`). | A draft's one-by-one line can never end up in a by-quantity category. | 2026-11-12 | 3.1 |
| B47 | **Line shape (from P1):** a "by quantity" line has a stock item and **no** category or description (its name comes from the stock item); a "one-by-one" line has a category and a **required** description. The database enforces this and "exactly one of stock item / category" with check constraints. Errors: `invalid_line`, `category_not_serialized`, `stock_item_inactive`, `category_inactive`, each with `details.line` (1, 2, …) so the screen marks the right line. | P1; keeps the two inventory models apart (PRD 9.1–9.2). | 2026-11-12 | 3.1 |
| B48 | **"Not in the future" uses the company timezone** (Q11): the purchase date is a calendar date (no time) and may be today or earlier in Asia/Kolkata. It is checked on create and when the date is changed. | Q11 / P3. Between midnight and 05:30 in India, UTC is still "yesterday": a UTC check would wrongly refuse today's date. | 2026-11-12 | 3.1 |
| B49 | **Cancelling asks for no reason** and stores no extra columns: who cancelled and when are in the audit log (`purchase.cancelled`, with the whole purchase before and after). Nothing is deleted. | The PRD lists no cancel reason; BR-13 is met by the audit row. Confirmed with the Slice 3.1 sign-off: no reason needed. | 2026-11-12 | 3.1 |
| B50 | **Purchase audit actions:** `purchase.created`, `purchase.updated` (only when something really changed), `purchase.cancelled` (already existed). Each records the vendor, reference, date, notes, status, the calculated total and every line (item, quantity, unit cost, line total). | BR-13, following B11. | 2026-11-12 | 3.1 |
| B51 | **Ready for receiving (3.2 / 3.3), enforced now by the database:** `received_date` may only be set on a received purchase; `received_quantity` is empty or 0 to the ordered quantity (P4: lower allowed, never higher). Received purchases already refuse edit and cancel (`purchase_not_draft`). | P4 / P6; no receiving code exists yet. | 2026-11-12 | 3.1 (3.2, 3.3) |
| B52 | **Screens:** the Purchases page lists purchases with search, status and vendor filters and Draft / Received / Cancelled badges (Draft orange, Received green, Cancelled grey outlined). New and edit use one form dialog (full screen on phones); a received or cancelled purchase opens in it read-only. The full purchase detail and history screens come in Slice 3.4. | Same dialog pattern as the other pages; 3.4 owns history (PUR-09). | 2026-11-12 | 3.1 (3.4) |
| B53 | **Pickers load the first 100 active records by name** (vendors, stock items, one-by-one categories); the vendor filter lists the first 100 vendors (active and inactive). A note appears if there are more vendors. Switch to search-as-you-type (like `EmployeePicker`) if lists grow past that. | Simple and enough for company-size master data. | 2026-11-12 | 3.1 |
| B54 | **Frontend tests (T1)** installed as dev-only packages at exact versions (section 3); `npm test` runs them once, `npm run test:watch` keeps watching. `jsdom` and `@testing-library/dom` are added because Vitest and React Testing Library need them. | T1 approved; exact versions requested by the owner. | 2026-11-12 | 3.1 |

---

## 15. Decisions in Slice 3.2 (⏳ pending sign-off)

B55–B59 are the owner's answers to the questions settled before coding (2026-11-13). The
others are technical or follow from Q1–Q3, P4–P6 and B14; all are **pending sign-off** with the slice.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| B55 | **A purchase is received in ONE step** (owner's answer; reading of Q2 "one receipt per purchase line"): one receiving form covers every line; each line is received once, with its received quantity. Saving receives the whole purchase, which becomes **Received** (final, P6). The request must list every line exactly once (`receipt_line_missing`, `invalid_receipt_line`). | Keeps purchase status to Draft / Received / Cancelled (PUR-04); no "partly received" state, which the PRD does not define. | 2026-11-13 | 3.2 (3.3) |
| B56 | **Purchases with by-quantity lines cannot be received until Slice 3.3** (owner's answer): receiving is refused with `bulk_receiving_unavailable` ("Receiving by-quantity items arrives in Slice 3.3", `details.lines` = the bulk line numbers). The screen shows the same message and no Receive button. Purchases with one-by-one lines only can be received now. | One-step receiving (B55) cannot leave bulk lines open. Slice 3.3 removes this block. | 2026-11-13 | 3.2 (3.3) |
| B57 | **Asset name = the line's description, editable per unit** (owner's answer): the receiving table pre-fills nothing in "Name"; an empty name is saved as the line's description (e.g. "Laptops: Dell Latitude 5440"). Required on the asset, at most 200 characters. | Every asset needs a name (AST-02); the description already says what was bought. | 2026-11-13 | 3.2 |
| B58 | **Quantities and dates** (owner's answer): a line may be received as **0** (nothing arrived; the line is closed with 0), but the receipt needs **at least 1 unit in total** (`nothing_received`). More than ordered is refused (`received_quantity_too_high`, P4); the number of unit rows must equal the received quantity (`unit_count_mismatch`). The **received date** may not be **before the purchase date** (`received_date_before_purchase`) or **in the future** in the company timezone (`received_date_in_future`, as B48). | P4 and Q2; a receipt that creates nothing would mark a purchase Received with no goods. | 2026-11-13 | 3.2 (3.3) |
| B59 | **A deactivated vendor or category does not block receiving** (owner's answer; closes the B45 question for 3.2): receiving a draft does not re-check them. Deactivation only blocks new purchases (B33) and new records (B13). | The goods have arrived; the receipt records what happened. Cancelling was already always allowed (B45). | 2026-11-13 | 3.2 (3.3 to confirm for stock items) |
| B60 | **The `assets` table** (migration 0009): asset ID **AST-000001, AST-000002, …** made by the database sequence `asset_code_seq` (Q3, BR-01), read-only, never reused (a failed save leaves a gap). Serial number and model required; brand, warranty expiry and location (typed, Q1) optional (P5). Purchase line, purchase date and cost (the line's unit cost) are copied from the receipt (AST-02) and are empty for manual entry (4.5). Status stored in lower case: `available`, `assigned`, `under_maintenance`, `damaged`, `retired` (PRD 8.1); new assets start as **available**. Created-by user stored. Never deleted (BR-12); all foreign keys RESTRICT. | Fits the asset register (4.1), edit/retire (4.2) and manual entry (4.5) without changes. | 2026-11-13 | 3.2 (4.1, 4.2, 4.5) |
| B61 | **Technical limits:** serial number and model 100 characters, brand 100, location 200, name 200; at most **1,000 assets per receipt** (`too_many_units`). Text is trimmed; empty optional text is stored as empty. Warranty expiry may be any date (the PRD sets no rule). | Limits are technical, not from the PRD. *Open: confirm no rule is needed for warranty expiry (e.g. not before the purchase date).* | 2026-11-13 | 3.2 |
| B62 | **Serial numbers unique across all assets, ignoring case** (AST-06, P5), enforced by the unique index `uq_assets_serial_number_lower`. Same serial twice in one receipt: `serial_number_duplicate`; used by an existing asset: `serial_number_taken`. Both carry `details.line` and `details.unit` (1, 2, …) so the screen marks the right row. One bad unit refuses the whole receipt; **nothing is saved**. If two receipts save the same serial at the same moment, the index lets only one win (the other gets `serial_number_taken`). | AST-06; the receipt is one transaction (PRD 10). | 2026-11-13 | 3.2 |
| B63 | **Assets lock their category's tracking type** (extends B14 / B46): any asset, whatever its status (retired too), counts as "category in use" (`tracking_type_locked`). | A one-by-one unit must never end up in a by-quantity category (PRD 9.2). | 2026-11-13 | 3.2 |
| B64 | **Audit on receipt (BR-13):** one `purchase.received` row (before: the draft; after: status, received date, each line's received quantity and new asset IDs) and one `asset.created` row per asset (ID, name, category, brand, model, serial, status, location, warranty, purchase number, line, purchase date, cost). Written in the same transaction as the receipt. | BR-13, following B11 / B50. | 2026-11-13 | 3.2 |
| B65 | **API and screens:** `POST /purchases/{id}/receive` (Admin and IT Manager, P6) returns the purchase with `lines[].received_quantity` and `lines[].assets` (id, asset ID, serial). `GET /assets/{id or asset ID}` (Admin and IT Manager) shows one asset with its purchase. Screen: a **Receive** icon on draft rows and a **Receive…** button in the draft form (disabled until changes are saved, because receiving uses the saved draft) open the receiving form: received date, received quantity per line, one row per unit, "copy unit 1's model, brand, warranty and location to all units", per-row errors, a confirm box, then a success message listing the new asset IDs. A received purchase shows "Received N of M" and clickable asset IDs (a small asset details box). The full asset register is Slice 4.1. | Build plan 3.2; PRD 13 (confirm before receiving). | 2026-11-13 | 3.2 (4.1) |
| B66 | **Frontend test time limit raised to 15 seconds** (`testTimeout` in `vite.config.js`). The Slice 3.1 test "saves a draft with laptops and mice" takes 5–7 s on a busy PC and failed at random against Vitest's 5 s default, with or without the Slice 3.2 changes. | Stops random failures; does not hide real ones (a broken test still fails). | 2026-11-13 | 3.2 |

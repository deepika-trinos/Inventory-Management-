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
2. **BR-12 (deactivate, don't delete):** Listed for employees (2.2) and vendors (2.3), but not for asset categories (2.1) or bulk stock items (2.4). Both of those are referenced by other records. *Categories: handled in Slice 2.1 (B13). Stock items: still to apply in Slice 2.4.*
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
| T1 | **Frontend automated tests:** approve a test tool (suggested: Vitest + React Testing Library)? None is approved yet, so the screens are checked manually. | Nothing; recommended before Phase 3 | When convenient |

**R1 is decided (see section 8). R3 is decided (see section 10). Nothing OPEN blocks Slices 2.3 or 2.4.**

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

## 11. Decisions in Slice 2.3 (pending the owner's sign-off of that slice)

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| B30 | **Vendor names are unique ignoring upper/lower case**, active or inactive (`vendor_name_taken`). Spaces at the ends are removed. | Owner's answer, 2026-11-12. Avoids look-alike vendors in the Slice 3.1 purchase picker; same rule as categories (B15). | 2026-11-12 | 2.3 |
| B31 | **Only the vendor name is required.** Contact person, email, phone and address are optional ("where available", VEN-02). Email is stored in lower case (B5), checked for format, and **may repeat** across vendors. Phone uses the employee phone check (B22). Limits: name and contact person 150, address 500 characters. | Owner's answers, 2026-11-12. | 2026-11-12 | 2.3 |
| B32 | **Vendor detail page at `/vendors/:id`** with Edit, Activate/Deactivate and a **Purchase history** section that is a placeholder until Slice 3.4 (VEN-04). The vendor name in the list links to it. | Owner's answer, 2026-11-12. Gives Slice 3.4 a page with its own address to fill in. | 2026-11-12 | 2.3 (3.4) |
| B33 | **Inactive vendors** stay readable and editable; only new purchases are blocked, through `ensure_vendor_active()` (`vendor_inactive`), which Slice 3.1 calls. Repeating activate/deactivate changes nothing and writes no audit row. | BR-12 / VEN-05; same pattern as categories (B13, B16) and employees (B28). | 2026-11-12 | 2.3 (3.1) |
| B34 | **Vendor search** (VEN-03) matches part of the name, contact person, email or phone, ignoring case; the only filter is status. Audit actions: `vendor.created`, `vendor.updated`, `vendor.activated`, `vendor.deactivated` (before/after of every field). | VEN-03 and BR-13 (B11). | 2026-11-12 | 2.3 |

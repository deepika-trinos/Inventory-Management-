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

**Slice 3.1 decisions B42–B54 are signed off (section 14). Slice 3.2 decisions B55–B66 are signed off (section 15). Slice 3.3 decisions C1–C12 are signed off (section 16). Slice 3.4 decisions D1–D10 are signed off (section 17). ✅ Phase 3 (Purchase and receiving) signed off by the owner on 2026-11-20, after all 18 manual test steps passed (`Phase3_WrapUp.md`). Slice 4.1 decisions E1–E10 are signed off (section 18, 2026-11-20); A1 is answered (E1); A2–A3 are answered (section 19, 2026-11-22); A4–A7 are still to be answered before Slices 4.4–4.5. Slice 4.2 decisions F1–F8 are signed off (section 20, 2026-11-22). Slice 4.3 decisions G1–G6 are signed off (section 21, 2026-11-23).** R1 is decided (see section 8). R3 is decided (see section 10). T1 is approved (see section 3). P1–P8 are decided (see section 13). Nothing OPEN blocks Phase 3.**

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
| B36 | **The unit locks once the item has stock** (`unit_locked`). ✅ **Active from Slice 3.3:** `_has_stock_history()` counts any stock movement (even when the balance is back to 0) or stock on hand. Name, category and threshold stay editable. | Owner's answer, 2026-11-12: 10 boxes must not silently become 10 pieces. | 2026-11-12 | 2.4 (3.3) |
| B37 | **Reorder threshold is required**, a whole number from 0 to 1,000,000; the form starts at 0. Low stock (Slice 4.3, INV-06) = quantity at or below the threshold, so 0 warns only when stock runs out. | Owner's answer, 2026-11-12. The upper limit is technical. | 2026-11-12 | 2.4 (4.3) |
| B38 | **A stock item can only be deactivated at zero stock** (`stock_not_zero`); issue or adjust it to 0 first (Slice 4.4). Never deleted (BR-12, closes gap 2 for stock items). Activating does not re-check the category. ✅ **Active from Slice 3.3** (confirmed): received stock blocks deactivation until the balance is 0; and an inactive item cannot receive stock (C5), so inactive always means zero stock. | Owner's answer, 2026-11-12. | 2026-11-12 | 2.4 (3.3, 4.4) |
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

## 15. Decisions in Slice 3.2 (✅ Slice 3.2 signed off by the owner, 2026-11-14; B55–B66 approved, B61 with the warranty rule)

B55–B59 are the owner's answers to the questions settled before coding (2026-11-13). The
others are technical or follow from Q1–Q3, P4–P6 and B14. **Signed off 2026-11-14.** B56 is superseded by Slice 3.3 (C9).

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| B55 | **A purchase is received in ONE step** (owner's answer; reading of Q2 "one receipt per purchase line"): one receiving form covers every line; each line is received once, with its received quantity. Saving receives the whole purchase, which becomes **Received** (final, P6). The request must list every line exactly once (`receipt_line_missing`, `invalid_receipt_line`). | Keeps purchase status to Draft / Received / Cancelled (PUR-04); no "partly received" state, which the PRD does not define. | 2026-11-13 | 3.2 (3.3) |
| B56 | ~~Superseded in Slice 3.3 (C9).~~ **Purchases with by-quantity lines cannot be received until Slice 3.3** (owner's answer): receiving is refused with `bulk_receiving_unavailable` ("Receiving by-quantity items arrives in Slice 3.3", `details.lines` = the bulk line numbers). The screen shows the same message and no Receive button. Purchases with one-by-one lines only can be received now. | One-step receiving (B55) cannot leave bulk lines open. Slice 3.3 removes this block. | 2026-11-13 | 3.2 (3.3) |
| B57 | **Asset name = the line's description, editable per unit** (owner's answer): the receiving table pre-fills nothing in "Name"; an empty name is saved as the line's description (e.g. "Laptops: Dell Latitude 5440"). Required on the asset, at most 200 characters. | Every asset needs a name (AST-02); the description already says what was bought. | 2026-11-13 | 3.2 |
| B58 | **Quantities and dates** (owner's answer): a line may be received as **0** (nothing arrived; the line is closed with 0), but the receipt needs **at least 1 unit in total** (`nothing_received`). More than ordered is refused (`received_quantity_too_high`, P4); the number of unit rows must equal the received quantity (`unit_count_mismatch`). The **received date** may not be **before the purchase date** (`received_date_before_purchase`) or **in the future** in the company timezone (`received_date_in_future`, as B48). | P4 and Q2; a receipt that creates nothing would mark a purchase Received with no goods. | 2026-11-13 | 3.2 (3.3) |
| B59 | **A deactivated vendor or category does not block receiving** (owner's answer; closes the B45 question for 3.2): receiving a draft does not re-check them. Deactivation only blocks new purchases (B33) and new records (B13). | The goods have arrived; the receipt records what happened. Cancelling was already always allowed (B45). | 2026-11-13 | 3.2 (3.3 to confirm for stock items) |
| B60 | **The `assets` table** (migration 0009): asset ID **AST-000001, AST-000002, …** made by the database sequence `asset_code_seq` (Q3, BR-01), read-only, never reused (a failed save leaves a gap). Serial number and model required; brand, warranty expiry and location (typed, Q1) optional (P5). Purchase line, purchase date and cost (the line's unit cost) are copied from the receipt (AST-02) and are empty for manual entry (4.5). Status stored in lower case: `available`, `assigned`, `under_maintenance`, `damaged`, `retired` (PRD 8.1); new assets start as **available**. Created-by user stored. Never deleted (BR-12); all foreign keys RESTRICT. | Fits the asset register (4.1), edit/retire (4.2) and manual entry (4.5) without changes. | 2026-11-13 | 3.2 (4.1, 4.2, 4.5) |
| B61 | **Technical limits:** serial number and model 100 characters, brand 100, location 200, name 200; at most **1,000 assets per receipt** (`too_many_units`). Text is trimmed; empty optional text is stored as empty. **Warranty expiry is optional, but when given it may not be before the purchase date** (`invalid_warranty_expiry`, with `details.line` / `details.unit`; checked on the screen too). | Limits are technical, not from the PRD. Warranty rule: owner's answer at sign-off, 2026-11-14 (catches typos such as 2019 for 2029; added in the Slice 3.3 branch). | 2026-11-13 (rule 2026-11-14) | 3.2 (3.3) |
| B62 | **Serial numbers unique across all assets, ignoring case** (AST-06, P5), enforced by the unique index `uq_assets_serial_number_lower`. Same serial twice in one receipt: `serial_number_duplicate`; used by an existing asset: `serial_number_taken`. Both carry `details.line` and `details.unit` (1, 2, …) so the screen marks the right row. One bad unit refuses the whole receipt; **nothing is saved**. If two receipts save the same serial at the same moment, the index lets only one win (the other gets `serial_number_taken`). | AST-06; the receipt is one transaction (PRD 10). | 2026-11-13 | 3.2 |
| B63 | **Assets lock their category's tracking type** (extends B14 / B46): any asset, whatever its status (retired too), counts as "category in use" (`tracking_type_locked`). | A one-by-one unit must never end up in a by-quantity category (PRD 9.2). | 2026-11-13 | 3.2 |
| B64 | **Audit on receipt (BR-13):** one `purchase.received` row (before: the draft; after: status, received date, each line's received quantity and new asset IDs) and one `asset.created` row per asset (ID, name, category, brand, model, serial, status, location, warranty, purchase number, line, purchase date, cost). Written in the same transaction as the receipt. | BR-13, following B11 / B50. | 2026-11-13 | 3.2 |
| B65 | **API and screens:** `POST /purchases/{id}/receive` (Admin and IT Manager, P6) returns the purchase with `lines[].received_quantity` and `lines[].assets` (id, asset ID, serial). `GET /assets/{id or asset ID}` (Admin and IT Manager) shows one asset with its purchase. Screen: a **Receive** icon on draft rows and a **Receive…** button in the draft form (disabled until changes are saved, because receiving uses the saved draft) open the receiving form: received date, received quantity per line, one row per unit, "copy unit 1's model, brand, warranty and location to all units", per-row errors, a confirm box, then a success message listing the new asset IDs. A received purchase shows "Received N of M" and clickable asset IDs (a small asset details box). The full asset register is Slice 4.1. | Build plan 3.2; PRD 13 (confirm before receiving). | 2026-11-13 | 3.2 (4.1) |
| B66 | **Frontend test time limit raised to 15 seconds** (`testTimeout` in `vite.config.js`). The Slice 3.1 test "saves a draft with laptops and mice" takes 5–7 s on a busy PC and failed at random against Vitest's 5 s default, with or without the Slice 3.2 changes. | Stops random failures; does not hide real ones (a broken test still fails). | 2026-11-13 | 3.2 |

## 16. Decisions in Slice 3.3 (✅ Slice 3.3 signed off by the owner; C1–C12 approved — recorded from the Slice 3.4 brief, 2026-11-16)

C1–C8 were explained to the owner and approved before coding (2026-11-14), as was "no audit row per stock movement".
C9–C12 are technical or follow from the brief. All were **approved with the Slice 3.3 sign-off** (the Slice 3.4 brief states Slices 3.1–3.3 are signed off).

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| C1 | **A by-quantity line received as 0 writes no stock movement**; the line is closed with "received 0". A receipt still needs at least 1 unit in total across all lines (B58). | Owner's answer. A movement's quantity is always above 0; a "+0" row would only clutter the history. | 2026-11-14 | 3.3 |
| C2 | **A movement stores two times:** `movement_date` = the business date (for a receipt, the received date; reports use it) and `created_at` = when it was saved (UTC). | Owner's answer; BR-09 "date/time". Goods received on 12 Nov but entered on 14 Nov are dated 12 Nov. | 2026-11-14 | 3.3 (4.3, 4.4) |
| C3 | **Reference / reason (BR-09):** a receipt's reference is its purchase line (`purchase_line_id`, so the history can show the purchase number). An optional `reason` text column (max 500, trimmed) exists now, empty for receipts; Slice 4.4 makes it required for adjustments (PRD: mandatory reason). | Owner's answer; avoids a second migration in 4.4. | 2026-11-14 | 3.3 (4.4) |
| C4 | **Each movement stores `balance_after`** (the item's balance right after it, never negative). | Owner's answer. The 4.3 history screen can show a running balance without recalculating, and it is an easy consistency check. | 2026-11-14 | 3.3 (4.3) |
| C5 | **A deactivated stock item refuses the receipt** when stock would arrive on it (`stock_item_inactive`, 409, `details.line`; nothing is saved). The screen warns on the line and asks to reactivate the item or enter 0. A line received as 0 does not block. Exception to B59 (vendors / categories do not block). | Owner's answer; keeps B38 true (an inactive item always has zero stock). | 2026-11-14 | 3.3 |
| C6 | **The same stock item on two lines** (allowed since 3.1, e.g. 10 mice at ₹300 and 5 at ₹350) gets **one movement per line**; the item's row is locked once and the balance rises by the total. | Owner's answer. The history matches the invoice line by line. | 2026-11-14 | 3.3 |
| C7 | **"Not enough stock" error = `insufficient_stock`** (409, `details` = stock item id, quantity on hand, requested), e.g. "Only 3 pieces of "HDMI cable" in stock (5 requested)". Raised by `record_movement()` for out-movements (issue, adjustment_out); taking stock exactly to 0 is allowed. Nothing in 3.3 takes stock out; tested directly. | Owner's answer; INV-07, BR-10. | 2026-11-14 | 3.3 (4.4) |
| C8 | **Receiving screen for by-quantity lines:** item name and unit, "By quantity · Ordered: 10 pieces", a received-quantity field filled with the ordered amount (0 to ordered), and "In stock now: 15 pieces · after receiving: 25 pieces". No unit rows. Footer and confirm box count assets and stock lines separately; the success message lists "stock added: USB mouse +10 pieces". A received purchase shows "Received 10 of 10 pieces (added to stock)". **Audit:** `purchase.received` gains `after.stock_received` = per by-quantity line: stock item, unit, received quantity, balance after. **No audit row per movement** (owner's answer): the append-only movement table is itself the history. | Owner's answers; BR-13. The purchase lines' `stock_item` now includes `quantity_on_hand` (read-only) for the "in stock now" hint. | 2026-11-14 | 3.3 |
| C9 | **Receiving by-quantity lines replaces B56:** `bulk_receiving_unavailable` is removed. Mixed purchases (e.g. 3 laptops + 10 mice) are received in one step (B55): assets for one-by-one lines, one `receipt` movement per by-quantity line with received quantity above 0. A by-quantity line sends no unit details (`units_not_allowed`). Everything (status, quantities, assets, movements, balances, audit) is ONE transaction; any failure saves nothing. | Brief; PUR-07, INV-03, B39. | 2026-11-14 | 3.3 |
| C10 | **The `stock_movements` table** (migration 0010): stock item, movement type (P7: `receipt`, `issue`, `adjustment_in`, `adjustment_out`, `opening`), quantity (> 0; the type says in or out), `balance_after` (>= 0), `movement_date`, `purchase_line_id`, `reason`, responsible user (`created_by_user_id`), `created_at`. Database checks: type list, quantity > 0, balance >= 0, and **a receipt always has a purchase line and other types never do**. All foreign keys RESTRICT. **Append-only:** an ORM guard refuses changes / deletes and a database trigger rejects UPDATE and DELETE (as the audit log, B11). | Brief; INV-05, BR-09, P7. | 2026-11-14 | 3.3 (4.3, 4.4, 4.5) |
| C11 | **One shared way to change stock:** `inventory.record_movement()` adds the movement and updates `quantity_on_hand` in the caller's transaction (no commit), refuses negative stock (C7) and programming mistakes (unknown type, quantity not above 0, receipt without purchase line). `inventory.lock_stock_items()` row-locks the items **in id order** (no deadlocks) and reloads their current balance and status first, so receipts saved at the same moment add up correctly. Slices 4.4 and 4.5 reuse both. | Brief; B39, PRD 10 (transactions). | 2026-11-14 | 3.3 (4.4, 4.5) |
| C12 | **Movement history has no screen or endpoint yet** (Slice 4.3). | Brief. | 2026-11-14 | 3.3 (4.3) |

---

## 17. Decisions in Slice 3.4 (✅ D1–D10 signed off by the owner, 2026-11-20)

**✅ Phase 3 (Purchase and receiving) signed off by the owner on 2026-11-20** (Slices 3.1–3.4,
decisions B42–B66, C1–C12, D1–D10), after the manual test run in `Phase3_WrapUp.md` section 2
passed on the TEST database.

D1 and D2 are the owner's answers given before coding (2026-11-16). D3–D7 are technical
or follow from the brief (no new business rules, no new write actions). D8 and D9 are the
owner's requests of 2026-11-19. **All of D1–D9 were approved by the owner on 2026-11-20, as
described below.** D10 is a small fix the owner asked for after the Phase 3 manual test run and **signed off with the phase** (2026-11-20). At approval the owner asked that D8 be strictly development-only; the
script was tightened the same day (see D8).

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| D1 | **Who received a purchase, and when, are stored on the purchase** (owner's answer): migration 0011 adds `received_by_user_id` (FK users, RESTRICT) and `received_at` (UTC, when the receipt was saved; the business date stays `received_date`, C2). Receiving fills both in the same transaction. Purchases received before 0011 are filled from their `purchase.received` audit row; one without such a row keeps both empty and the detail page says "Not recorded". A database check keeps both empty unless the purchase is received. | PUR-09 / the brief ("who received it, and when"). Simple to read; the audit log stays the full history (BR-13). | 2026-11-16 | 3.4 |
| D2 | **A vendor's purchase history is newest purchase date first** (owner's answer); purchases with the same date are ordered by purchase number, newest first. Every purchase list now breaks ties by purchase number in the sort's direction, so paging never repeats or skips a row. | VEN-04 "newest first"; invoices are read by date. | 2026-11-16 | 3.4 |
| D3 | **Date-range filter = the purchase date**, `date_from` and `date_to`, both days included; either may be left out. `date_from` after `date_to`: **422** `invalid_date_range` (the screen also marks the "to" field red). The list can also be sorted by received date (not-yet-received purchases last when ascending). | The brief names the purchase-date range. | 2026-11-16 | 3.4 |
| D4 | **Vendor purchase history reuses `GET /purchases?vendor_id=…`** (no new endpoint): same row fields as the list (reference, vendor, purchase date, received date, status, number of lines, total in INR); all statuses; inactive vendors included. An unknown `vendor_id` now answers **404** `vendor_not_found` instead of an empty list. | The brief ("reuse the list endpoint with a vendor filter; unknown vendor gives 404"). | 2026-11-16 | 3.4 |
| D5 | **Purchase detail = `GET /purchases/{id}`, extended:** the vendor now carries its contact details (contact person, email, phone, address) in every full purchase response; each line adds `stock_movements` (type, quantity, balance after, date, saved at, by whom) next to the existing `assets` (asset ID, serial); `received_by` and `received_at` are added. Totals stay calculated by the server. The receive response returns the same shape, movements included. | PUR-09 "linked vendor/item details"; one shape for detail and receipt. | 2026-11-16 | 3.4 |
| D6 | **Screens:** detail page `/purchases/:id` (same roles as Purchases): details, lines with ordered / received quantities, unit cost, line totals and total, **Assets created** (click an asset ID for its details) and **Stock movements**, each with an empty message that says why (draft: "created when received"; cancelled: "never changes stock or creates assets"). Received and cancelled purchases are read-only; a draft keeps its existing Edit / Receive… / Cancel purchase actions (no new write actions). On the Purchases list the purchase number and **View** open the detail page (Edit stays a dialog for drafts); new "Purchase date from / to" filters, a Received column and **Clear filters**. The vendor page's placeholder is replaced by its purchase history (5 / 10 / 20 rows per page); clicking a row (or Enter / Space on it) opens the purchase. | The brief; same page pattern as the vendor detail page (B32). | 2026-11-16 | 3.4 |
| D7 | **Shared table option:** `DataTable` gains `onRowClick` / `rowLabel` (rows open something by mouse or keyboard). Used by the vendor history; the Purchases list keeps explicit links because its rows also have action buttons. | Reused by later history lists (4.1, 4.3). | 2026-11-16 | 3.4 |
| D8 | **Development-only `reset_password` script** (owner's request, 2026-11-19, after the dev Admin's password was lost): `python -m app.scripts.reset_password --email …` sets a new password for an existing login. **Strictly development-only (tightened at approval, 2026-11-20):** it runs only when `APP_ENV` is explicitly set to `development` (in `backend\.env` or the environment) and refuses `production`, `test` and an `APP_ENV` that is not set at all (the app's default is `development`, so a server that forgot to set it must not count as a developer's machine); tested for all four cases. It asks for the password twice without showing it, applies `PASSWORD_MIN_LENGTH`, changes nothing else (a deactivated login stays deactivated) and writes a `user.updated` audit row as a system action (no actor; the password is never logged or printed). **This is not the R2 decision:** a real "forgot / reset password" feature for users is still OPEN (R2, before Slice 8.3). | `create_admin` does nothing once an active Admin exists, and the app has no reset, so a lost dev password blocked testing. | 2026-11-19 | 3.4 branch (tooling) |
| D9 | **Clearer category filters** (owner's request, 2026-11-19, after Phase 1–3 testing): the Tracking and Status filters still combine (both must match; the server logic was correct and is unchanged). The Categories page now shows **Clear filters** while a filter is set, and an empty result caused by filters or search says **"No matches"** (with a button to clear the search and filters) instead of the misleading "No categories yet". Built into the shared `DataTable` (`filtersActive`, `onClearFilters`). **Also applied to Vendors (Status), Employees (Department, Status) and Inventory (Category, Status)** at the owner's request the same day. Purchases keeps its own Clear filters button (D6); Users is unchanged. No data or business rules changed. | Testing found "Inactive" and "By quantity" looking broken: the other filter was still set, and the empty message suggested no categories existed. | 2026-11-19 | 3.4 branch (fix) |
| D10 | **"No matches" on the Purchases list too** (owner's request, 2026-11-20, from the Phase 3 manual test run, step 11): when the Status, Vendor or purchase-date filters give an empty result, the Purchases list now says **"No matches"** with a button that clears the filters, instead of the misleading "No purchases yet" (D9's `filtersActive` / `onClearFilters`, which D9 had left off Purchases). A "from" date after the "to" date is still explained in the table and the "to" field stays red, but the message no longer offers a useless **Try again** (new optional `DataTable` prop `canRetry`; every other list keeps Try again). No data, server or business rules changed. | Testing showed "No purchases yet" while 7 purchases existed. | 2026-11-20 | 3.4 branch (fix at sign-off) |

---

## 18. Decisions in Slice 4.1 (✅ Slice 4.1 signed off by the owner, 2026-11-20; E1–E10 approved)

E1–E4 are the owner's answers given before coding (2026-11-20). The others are technical
or follow from the brief and earlier decisions (no new business rules, no new write
actions, no migration). E10 is a fix the owner approved during the combined test run. **All of
E1–E10 were approved with the Slice 4.1 sign-off (2026-11-20)**, after 622 backend and 126
frontend tests passed on the combined 4.1 + Phase 3 code and the browser check on the TEST
database passed.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| E1 | **A1 answered: no employee filter in 4.1** (owner's answer). The asset register has no employee filter or column; Slice 5.1 adds them together with assignments. | Assignments don't exist yet, so the filter would always be empty. | 2026-11-20 | 4.1 (5.1) |
| E2 | **The asset page's "full history" = every audit log row about the asset** (owner's answer): `entity_type = "assets"` and the asset's id, newest first, with who did it (or "System"), paged on the server (`GET /assets/{id or asset ID}/history`). In 4.1 that is the `asset.created` row ("Received on purchase PUR-…"); edit / retire (4.2), assign / return (5.x) and maintenance (6.x) add theirs automatically by writing audit rows for the asset. No new table. | BR-13: the audit log is already the complete history; one source, nothing to keep in step. | 2026-11-20 | 4.1 (4.2, 5.x, 6.x) |
| E3 | **Location filter = the whole location, ignoring upper/lower case** (owner's answer; same as the department filter, B23). Choices come from `GET /assets/locations`: every location already typed, one spelling per location ignoring case, A–Z. | Location is typed text (Q1). | 2026-11-20 | 4.1 |
| E4 | **Branching** (owner's answer): Slice 3.4 was committed locally on `phase3/slice-3.4-purchase-history` (not pushed or merged), and `phase4/slice-4.1-asset-register` was branched from it, because 4.1 reuses 3.4's shared pieces (paging tiebreaker, D7 clickable rows, D9 Clear filters / "No matches"). After the Phase 3 sign-off (2026-11-20), 3.4 and the sign-off commit were merged into the local `development` (fast-forward, not pushed) and `phase4/slice-4.1-asset-register` was moved onto it (`bcac13b`); the 4.1 work was restored there from its stash. | At the time, `development` still stopped at Slice 3.3. | 2026-11-20 | 4.1 |
| E5 | **Asset name = the `name` field** already decided in B57 (the purchase line's description unless typed per unit). Search matches **part of the asset ID, serial number or name**, ignoring case (`%` and `_` are plain characters); model, brand and location are not searched. | Build-plan done-check: "found by ID, serial or name". | 2026-11-20 | 4.1 |
| E6 | **`GET /assets` (Admin and IT Manager; Employee 403):** filters `category_id` (any category, active or inactive; unknown: **404** `category_not_found`, as D4), `status` (one of the five PRD 8.1 statuses; anything else: **422** `validation_error`) and `location` (E3). Filters and search combine. Sort by asset ID, name, category, brand, model, serial number, status, location, warranty expiry or created; **default newest asset ID first**; ties broken by id in the sort's direction (shared `paginate()` tiebreaker), so paging never repeats or skips a row. Unknown sort field: **400** `invalid_sort` (shared helper, unchanged). | Brief; same patterns as the other lists. Newest first shows just-received assets on page 1. | 2026-11-20 | 4.1 |
| E7 | **`GET /assets/{id or asset ID}` extended:** the purchase summary adds `vendor_id` (so the asset page can link to the vendor). Created by and created at were already returned. | Brief ("purchase link, created by/when"). | 2026-11-20 | 4.1 |
| E8 | **Screens:** **Assets** menu item (Admin and IT Manager) with the shared `DataTable`: columns Asset ID, Name, Category, Serial number, Model (brand + model), Location, Status; search; Category (one-by-one categories, inactive marked, first 100 by name as B53), Status and Location filters; Clear filters and "No matches" (D9); clickable rows (D7). Asset page `/assets/:assetId` (asset ID or id) with **Details**, **Purchase** (links to the purchase and vendor; "No purchase" when entered by hand) and **History** (5 / 10 / 20 rows per page); "Asset not found" with a link back. No write actions. The small asset box on a received purchase (B65) is unchanged. | Brief; same page pattern as purchases (D6). | 2026-11-20 | 4.1 |
| E9 | **No migration and no index added.** "Contains" searches scan the table anyway (as B27); the location filter compares lower(location). Fine at company size; revisit if assets grow into the tens of thousands. | Keep the slice small; nothing to migrate. | 2026-11-20 | 4.1 |
| E10 | **Stock-items list gets a tie-breaker** (owner's approval, 2026-11-20): items with the same sort value (e.g. two in one category, or the same reorder threshold) are ordered by id in the sort's direction (shared `paginate()` tiebreaker, as D2 for purchases and E6 for assets). Found when the combined 4.1 + Phase 3 test run failed once on `test_list_search_filters_and_sort` (the order of two same-category items was left to the database); the test then passed 30 of 30 runs alone, so it was intermittent, not caused by 4.1. One-line change in `inventory.list_stock_items()` plus a test of the tie order and of paging. No data or business rules changed. | Stable order; paging never repeats or skips a row. | 2026-11-20 | 4.1 branch (fix to Slice 2.4 code) |

---

## 19. Phase 4 questions answered by the owner (for Slice 4.2)

Answers to A2 and A3 from `Phase3_WrapUp.md` section 3, given by the owner on 2026-11-22
(the recommended options, accepted as written). A4–A7 are still open (Slices 4.4–4.5).

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| A2 | Which asset fields can be edited after creation? | **Editable:** name, brand, model, serial number (still unique ignoring case, AST-06 / B62; old and new value in the audit log), location, warranty expiry (still not before the purchase date, B61). **Locked on assets received from a purchase:** category, purchase link, purchase date and cost (they come from the invoice, so purchase totals keep matching their assets; P6). **Manually entered assets (Slice 4.5):** those fields are editable too, the category only among one-by-one categories (B14 / B63); no purchase link. **Never editable:** asset ID (Q3) and status (changes only through actions, AST-07). | 2026-11-22 | 4.2 (4.5) | Decided |
| A3 | From which statuses can an asset be retired, and what is the reason? | **Retire only from Available or Damaged.** An Assigned asset is returned first (Phase 5); an asset Under Maintenance has its repair finished first (Phase 6, which may revisit this). An already Retired asset cannot be retired again. **Reason:** free text, required, up to 500 characters (same as the stock-adjustment reason, Q7 / C3). **Also decided:** a retired asset is fully read-only (no edits; retiring cannot be undone); only Admin and IT Manager can retire (Employee: 403). | 2026-11-22 | 4.2 (5.x, 6.x) | Decided |

---

## 20. Decisions in Slice 4.2 (✅ Slice 4.2 signed off by the owner, 2026-11-22; F1–F8 approved)

F1 and F2 are the owner's answers given before coding (2026-11-22). The others are technical or
follow from A2, A3 and earlier decisions (no new business rules). **All of F1–F8 were approved
with the Slice 4.2 sign-off (2026-11-22)**, after 676 backend and 146 frontend tests passed and
the browser check on the TEST database passed.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| F1 | **Manual-entry editing is deferred to Slice 4.5** (owner's answer): in 4.2, category, purchase date and cost stay locked on **every** asset (today every asset comes from a purchase). Slice 4.5 adds editing them for manually entered assets once A7 decides its rules (e.g. whether that purchase date may be in the future). | A2 allows it for manual entries, but their rules are still open (A7). Nothing is guessed. | 2026-11-22 | 4.2 (4.5) |
| F2 | **Retirement details are stored on the asset** (owner's answer): migration 0012 adds `retired_at` (UTC, database time), `retired_by_user_id` (FK users, RESTRICT) and `retire_reason` (up to 500). Filled in the same transaction as the `asset.retired` audit row. A check constraint keeps all three empty unless the asset is retired. No backfill: there was no way to retire before; an asset marked retired by hand shows "Not recorded". Checked on the TEST database only (upgrade, downgrade, upgrade; `alembic check` clean). | Same approach as D1 (received by / at): simple to read for the page and later reports; the audit log stays the full history (BR-13). | 2026-11-22 | 4.2 (7.x) |
| F3 | **A3 as recorded in section 19 is followed**, not the brief's older suggestion ("not while Assigned"): retiring is allowed **only from Available or Damaged**. | The owner's recorded answer (2026-11-22) is stricter and newer. | 2026-11-22 | 4.2 |
| F4 | **`PATCH /assets/{id or asset ID}`** accepts only name, brand, model, serial number, location, warranty expiry (A2). Any other field (status, category, purchase date, cost, asset ID, purchase link, retirement fields) is refused as a whole with **422** `validation_error`. Send only what changes; `null` clears brand, location or warranty; name, model and serial cannot be emptied (`invalid_asset_name` / `invalid_model` / `invalid_serial_number`). Same limits and trimming as on receipt (B61). An edit that changes nothing saves nothing and writes no audit row (as B16). Assets can be edited in any status except Retired. | A2; AST-07 (status only through actions); same patterns as the other records. | 2026-11-22 | 4.2 |
| F5 | **Error codes** (shared error format): `asset_retired` (409, edit or retire a retired asset); `asset_not_retirable` (409, Assigned or Under Maintenance, `details.status`, message says "Return it first." / "Finish the repair first."); `invalid_retire_reason` (422, missing, blank or over 500); `serial_number_taken` (409, reused from B62); `invalid_warranty_expiry` (422, B61). | Clear codes the screen can show; reuse existing ones. | 2026-11-22 | 4.2 |
| F6 | **Audit (BR-13):** new action `asset.updated` (added to the agreed action list) with `before` / `after` holding only the changed fields (A2: old and new value); `asset.retired` with before `{status}` and after `{status: retired, reason}`. Written in the same transaction as the change; a failure saves nothing (tested by forcing the audit write to fail). | BR-13; the asset page's History (E2) shows them without extra work. | 2026-11-22 | 4.2 |
| F7 | **Row lock:** edit and retire lock the asset row (`FOR UPDATE OF assets`) and reload it first, so two people acting at the same moment cannot both act on an out-of-date status (tested: two simultaneous retires, one wins, the other gets `asset_retired`, one audit row). | PRD 10 (transactions); same idea as C11. | 2026-11-22 | 4.2 |
| F8 | **Screens:** the asset page gets **Edit** (dialog with only the editable fields; asset ID, status, category, purchase, purchase date and cost shown read-only under "Cannot be changed here"; a taken serial is shown under the serial field) and **Retire…** (confirm box: "permanent and cannot be undone", required reason with a 0 / 500 counter; greyed out with a tooltip unless Available or Damaged). A retired asset shows "Retired assets are final. Read-only.", **Retired by** (who · when) and **Reason for retiring**, and has no Edit or Retire. History shows "Edited · Location: A → B; Serial number: X → Y" and "Retired · Reason: …". Only Admin and IT Manager (Employee: 403, as E6). | The brief; A2, A3. | 2026-11-22 | 4.2 |

---

## 21. Decisions in Slice 4.3 (✅ Slice 4.3 signed off by the owner, 2026-11-23; G1–G6 approved)

G1 and G2 are the owner's answers to the plan (2026-11-22, approved with the plan). The others
are technical or follow from B37, C2–C4 and C12 (no new business rules, no new way to change
stock, no migration). **All of G1–G6 were approved with the Slice 4.3 sign-off (2026-11-23)**,
after 696 backend and 158 frontend tests passed and the browser check on the TEST database passed.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| G1 | **Only active items are flagged as low stock** (owner's answer): `low_stock` = status Active **and** quantity on hand at or below the reorder threshold (B37). An inactive item (always 0, B38) is never flagged; the Low stock filter shows active items only. | Inactive items cannot be restocked (C5) or used, so flagging them would clutter the list. | 2026-11-22 | 4.3 |
| G2 | **Movement history is newest first in the order SAVED** (owner's answer), with ties broken by id (movements saved together, C6, keep their order). Each row shows both the business date (C2) and when it was saved. | `balance_after` (C4) then reads as a running balance; sorting by business date could make a late-entered receipt look out of order. | 2026-11-22 | 4.3 |
| G3 | **The flag is calculated, never stored**: one rule on the model (`StockItem.low_stock`, and the same rule in SQL for the filter). **No migration**: the history reads the existing `stock_movements` table (indexed by stock item). | Cannot go out of date when a balance or threshold changes; nothing to backfill. | 2026-11-22 | 4.3 |
| G4 | **API:** every stock item response gains `low_stock`; `GET /stock-items?low_stock=true|false` (combines with search, category, status; a bad value: 422 `validation_error`); new `GET /stock-items/{id}/movements` (paged; type, `direction` in/out, `quantity`, signed `change`, `balance_after`, `movement_date`, `created_at`, `created_by`, `reason`, `reference` = the receipt's purchase number and line, empty for other types). Unknown item: 404 `stock_item_not_found`. Inactive items keep their history. Admin and IT Manager only (Employee: 403). | INV-02, INV-05, INV-06; C3 (a receipt's reference is its purchase line). | 2026-11-22 | 4.3 |
| G5 | **Screens:** Inventory list: orange **Low stock** badge next to "On hand", **Stock level** filter (All / Low stock) with Clear filters and "No matches" (D9); the item name links to the new **stock item page** `/inventory/:id` (the row itself is not clickable because it has Edit / Deactivate buttons, as on Purchases, D7). The page shows quantity on hand, reorder threshold, stock level (low / above / inactive), category, unit, status, added and last changed; reuses the existing Edit and Activate / Deactivate boxes; and lists the **Movement history** (date, type, +/- change, balance after, reference linking to the purchase, reason, saved at and by whom; 10 / 20 / 50 per page). | The plan approved by the owner (2026-11-22). | 2026-11-22 | 4.3 |
| G6 | **C12 is now done**: the movement history has its endpoint and screen. Issues, adjustments (4.4) and opening stock (4.5) will appear in it automatically. | C12 said "Slice 4.3". | 2026-11-22 | 4.3 (4.4, 4.5) |

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

1. **BR-13 (traceability):** Slices 4.4 (stock issue/adjust), 5.2 (return) and 6.2 (maintenance status changes) don't mention writing an audit log entry. *Resolved for stock changes in Slice 4.4 (H6: `stock.issued`, `stock.adjusted`), for returns in Slice 5.2 (K6: `assignment.returned`) and for maintenance status changes in Slice 6.2 (U6: `maintenance.status_changed`, `maintenance.updated`).* BR-13 requires it. Slice 8.1's done-check expects returns and stock changes in the audit log.
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

**Phase 1 (Slices 1.1–1.6, decisions B1–B12) is signed off (section 8, 2026-11-23). Slice 3.1 decisions B42–B54 are signed off (section 14). Slice 3.2 decisions B55–B66 are signed off (section 15). Slice 3.3 decisions C1–C12 are signed off (section 16). Slice 3.4 decisions D1–D10 are signed off (section 17). ✅ Phase 3 (Purchase and receiving) signed off by the owner on 2026-11-20, after all 18 manual test steps passed (`Phase3_WrapUp.md`). Slice 4.1 decisions E1–E10 are signed off (section 18, 2026-11-20); A1 is answered (E1); A2–A3 are answered (section 19, 2026-11-22); A4–A5 are answered (section 22, 2026-11-23); A6–A7 are answered (section 24, 2026-11-23). Slice 4.2 decisions F1–F8 are signed off (section 20, 2026-11-22). Slice 4.3 decisions G1–G6 are signed off (section 21, 2026-11-23). Slice 4.4 decisions H1–H8 are signed off (section 23, 2026-11-23). Slice 4.5 decisions I1–I8 are signed off (section 25, 2026-11-23). ✅ Phase 4 (Asset and inventory operations) signed off by the owner on 2026-11-23 (`Phase4_WrapUp.md`). Phase 5 questions A1 and N1–N9 are answered (section 26, 2026-11-23). Slice 5.1 decisions J1–J10 are signed off (section 27, 2026-11-23). Slice 5.2 decisions K1–K8 are signed off (section 28, 2026-11-24). Phase 5 questions N10–N15 are answered (section 29, 2026-11-24). Slice 5.3 decisions L1–L8 are signed off (section 30, 2026-11-24). Phase 6 questions O1–O14 are answered (section 31, 2026-11-24). Slice 6.1 decisions M1–M8 are signed off (section 32, 2026-11-25). Phase 6 questions S1–S14 are answered (section 33, 2026-11-25). Slice 6.2 decisions U1–U9 are signed off (section 34, 2026-11-25). Slice 6.3 decisions V1–V9 are signed off (section 36, 2026-11-26). Slice 6.4 decisions W1–W6 are signed off (section 38, 2026-11-26).** R1 is decided (see section 8). R3 is decided (see section 10). T1 is approved (see section 3). P1–P8 are decided (see section 13). Nothing OPEN blocks Phase 3.**

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

## 8. Decisions in Slices 1.5–1.6 (✅ signed off with Phase 1 by the owner, 2026-11-23)

**✅ Phase 1 (Foundation) signed off by the owner on 2026-11-23** (Slices 1.1–1.6, decisions B1–B12,
R1, order fixes a–c). Phase 1 was completed on 2026-11-11 (commit `976317c`) and has been in use
since; this sign-off was recorded afterwards, when a progress review found that no Phase 1 sign-off
entry existed. B7–B12 are approved with it.

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
| A3 | From which statuses can an asset be retired, and what is the reason? | **Retire only from Available or Damaged.** An Assigned asset is returned first (Phase 5); an asset Under Maintenance has its repair finished first (Phase 6, which may revisit this). An already Retired asset cannot be retired again. **Reason:** free text, required, up to 500 characters (same as the stock-adjustment reason, Q7 / C3). **Also decided:** a retired asset is fully read-only (no edits; retiring cannot be undone); only Admin and IT Manager can retire (Employee: 403). | 2026-11-22 | 4.2 (5.x, 6.x) | Decided (Under Maintenance: revised by T7, section 35) |

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

---

## 22. Phase 4 questions answered by the owner (for Slice 4.4)

Answers to A4 and A5 from `Phase3_WrapUp.md` section 3, plus three related points raised with
them, given by the owner on 2026-11-23 (the recommended options, accepted as written). A6 and A7
are still open (Slice 4.5). Already fixed and unchanged: every issue and adjustment needs a
reason (free text, up to 500, C3) and a confirm box, with no approval step (Q7); stock never
goes below 0, exactly 0 is allowed (C7, INV-07); balance and movement are saved in one
transaction and appear in the item's movement history with who did it (B39, C11, G6).

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| A4 | Must a stock issue name who received the items? | **Employee optional, reason required.** An issue may name **one active employee** (EMP-05: inactive employees get nothing new) when the items went to a person; issues to a room, event or team name no employee and say so in the reason. The employee is recorded on the movement (a nullable link from `stock_movements` to `employees`, so a small migration) and shown in the movement history, e.g. "Issued to Asha Kumar (EMP-001)". Issued stock does **not** appear in the employee's My Assets (consumables are counted, not tracked per person, PRD 9.2). | 2026-11-23 | 4.4 | Decided |
| A5 | How is a stock adjustment entered? | **"Add / Remove N" with a required reason.** The person chooses Add (`adjustment_in`) or Remove (`adjustment_out`, P7) and the quantity; the form shows "On hand now … · after …" before confirming (like the receiving form, C8). Removing more than is in stock is refused (`insufficient_stock`, C7). A counted-stocktake mode ("set to counted N") is **not** built now; it can be added later if regular counts are needed. | 2026-11-23 | 4.4 | Decided |
| A4-5a | Date of an issue or adjustment | **Today by default; an earlier date is allowed, a future date is refused** (company timezone), the same as receiving (B58) and purchase dates (B48). It is the movement's business date (C2). | 2026-11-23 | 4.4 | Decided |
| A4-5b | One screen or separate actions? | **Separate actions on the stock item page: "Issue…" and "Adjust…"**, each with its own confirm box and fields. | 2026-11-23 | 4.4 | Decided |
| A4-5c | Who can issue and adjust? | **Admin and IT Manager only** (Employee: 403), the same as every other stock action. | 2026-11-23 | 4.4 | Decided |

---

## 23. Decisions in Slice 4.4 (✅ Slice 4.4 signed off by the owner, 2026-11-23; H1–H8 approved)

H1–H3 restate the owner's answers recorded in section 22 (A4, A5, A4-5a/b/c, 2026-11-23); the
brief's "stop and ask" points (date in the past or future; department on an issue) were already
answered there. The others are technical or follow from Q7, P7, B38, B41, C2, C3, C7, C10 and C11.
**All of H1–H8 were approved with the Slice 4.4 sign-off (2026-11-23)**, after 747 backend and 173
frontend tests passed and the browser check on the TEST database passed.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| H1 | **Issue** (A4): `POST /stock-items/{id}/issue` with quantity, a required reason, an **optional active employee** (`employee_id`; unknown: 404 `employee_not_found`, inactive: 409 `employee_inactive`) and an optional date. No department field: an issue to a room, event or team names no employee and says so in the reason. Migration 0013 adds `stock_movements.issued_to_employee_id` (FK employees, RESTRICT), with a check constraint that only an `issue` may name one; checked on the TEST database only (upgrade, downgrade, upgrade; `alembic check` clean). The employee is shown in the movement history and recorded in the audit row. | A4 (section 22). | 2026-11-23 | 4.4 |
| H2 | **Adjust** (A5): `POST /stock-items/{id}/adjust` with `direction` `add` (`adjustment_in`) or `remove` (`adjustment_out`), quantity and a required reason. No counted-stocktake mode. An adjustment cannot name an employee (422 `validation_error`). | A5 (section 22). | 2026-11-23 | 4.4 |
| H3 | **Date** (A4-5a): `movement_date` defaults to today in the company timezone; an earlier date is allowed; a future date: 422 `movement_date_in_future`. It is the business date (C2); the history stays in saved order (G2). | A4-5a (section 22). | 2026-11-23 | 4.4 |
| H4 | **Shared rules for both:** reason required, trimmed, up to 500 (`invalid_reason`, Q7 / C3); quantity a whole number from 1 to 1,000,000 (technical limit, like the reorder threshold B37; otherwise 422 `validation_error`); unknown fields refused; never below 0 (409 `insufficient_stock` with `details` = item, on hand, requested; exactly 0 allowed, C7); inactive item 409 `stock_item_inactive` (B38, B41); unknown item 404 `stock_item_not_found`. No approval step (Q7). Admin and IT Manager only (A4-5c; Employee 403). | Q7, C3, C7, B38, B41. | 2026-11-23 | 4.4 |
| H5 | **One path, one transaction (B39, C11):** both actions lock the item row (`lock_stock_items`), check everything, write the movement and new balance through `record_movement()`, write the audit row and commit together; any failure rolls everything back (tested by forcing the audit write to fail). Two issues at the same moment cannot take stock below 0 (tested: one succeeds, the other gets `insufficient_stock`, one movement). The balance always equals the newest movement's `balance_after`. | Build plan 4.4; PRD 10. | 2026-11-23 | 4.4 |
| H6 | **Audit (BR-13; closes coverage gap 1 for stock changes):** `stock.issued` and `stock.adjusted` on the stock item, `before` = quantity on hand, `after` = new quantity on hand, movement id, type, quantity, date, reason and (issues) the employee. Receipts keep their `purchase.received` row (C8). | Coverage gap 1 in section 1; the brief. | 2026-11-23 | 4.4 |
| H7 | **Responses:** both return `{item, movement}`: the item with its new balance and low-stock flag, and the movement in the same shape as the history rows (with `issued_to`). The history (G4) gains `issued_to` on every row. | One shape for the page to update itself. | 2026-11-23 | 4.4 |
| H8 | **Screens:** the stock item page gets **Issue…** and **Adjust…** (A4-5b; greyed out with "Activate the item first." for inactive items). Each opens a form (quantity with "On hand now … · after …" while typing, reason with a 0 / 500 counter, date, and for an issue "Issued to (optional)" listing active employees; for an adjustment Add or Remove), then a confirm box ("Issue 3 pieces of USB mouse?", balance now and after, employee, date and reason, and "Stock movements are permanent: a mistake is corrected with a new adjustment."). The screen checks quantity, stock, reason and date first; a server refusal returns to the form with the message under the field. After saving: a message with the new balance, and the page and history refresh. The shared `EmployeePicker` gains `onlyWithoutLogin` (default unchanged for the Users screen). | The brief; A4, A5. | 2026-11-23 | 4.4 |

---

## 24. Phase 4 questions answered by the owner (for Slice 4.5)

Answers to A6 and A7 from `Phase3_WrapUp.md` section 3, plus two related points raised with them,
given by the owner on 2026-11-23 (the recommended options, accepted as written). Already fixed and
unchanged: asset IDs come from the system sequence (Q3); serial numbers are unique ignoring case
(AST-06, B62); manual entry is for one-by-one items and opening stock for by-quantity items (Q4).

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| A6 | Opening stock: how often, and who? | **Once per item, only while the item has no movements at all; Admin and IT Manager.** After any receipt, issue or adjustment, the balance is corrected with Adjust. | 2026-11-23 | 4.5 | Decided |
| A7 | Manual asset entry: which fields? | **Like receiving.** Required: an active one-by-one category, serial number (unique, any case), model and name (typed, since there is no purchase line to name it after). Optional: brand, location, warranty expiry, purchase date, cost. **No vendor.** Always created as **Available**. Admin and IT Manager. | 2026-11-23 | 4.5 | Decided |
| A7a | Purchase date, cost and later edits | Purchase date optional and **not in the future** (company timezone, as B48); cost 0 or more with 2 decimals (P2); warranty not before the purchase date (B61). After creation, **category (one-by-one only), purchase date and cost are editable on manual assets only** (completes A2); received assets keep them locked. | 2026-11-23 | 4.5 | Decided |
| A6a | Opening stock form | **Quantity** (whole number, 1 or more); **date** today by default, earlier allowed, future refused (as A4-5a); **optional note**; the history shows "Opening stock"; an inactive item is refused; a **confirm box** shows 0 → N. | 2026-11-23 | 4.5 | Decided |

---

## 25. Decisions in Slice 4.5 (✅ Slice 4.5 signed off by the owner, 2026-11-23; I1–I8 approved)

I1–I3 and I5 restate the owner's answers in section 24 (A6, A6a, A7, A7a, 2026-11-23). The others
are technical or follow from Q3, Q4, P2, B13, B39, B48, B61, B62, C11 and H5. **All of I1–I8 were
approved with the Slice 4.5 sign-off (2026-11-23)**, after 815 backend and 195 frontend tests passed
and the browser check on the TEST database passed.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| I1 | **Manual asset entry** (A7): `POST /api/v1/assets` (201) creates ONE asset without a purchase: `purchase_line_id` empty, status **Available**, `created_by` the user, the **next asset ID from the same sequence as receiving** (`asset_code_seq`; tested: receiving and manual entries interleave as AST-000003, AST-000005). Required: `category_id`, `serial_number`, `model`, `name`; optional: `brand`, `location`, `warranty_expiry`, `purchase_date`, `cost`. Status, vendor, purchase link, quantity, asset ID or any other field: 422 `validation_error`. | A7; Q3, Q4. | 2026-11-23 | 4.5 |
| I2 | **Same checks as receiving:** text trimmed and limited exactly as for received units (`clean_unit`, P5: `invalid_serial_number`, `invalid_model`, `invalid_asset_name`, `invalid_brand`, `invalid_location`); serial unique ignoring case against every asset (409 `serial_number_taken`, also caught from the database index if two people save at the same moment, B62); category must exist (404 `category_not_found`), be tracked one by one (409 `category_not_serialized`, B13) and be active (409 `category_inactive`). | A7; AST-06; B13, B62. | 2026-11-23 | 4.5 |
| I3 | **Dates and cost** (A7a): `purchase_date` optional, never in the future (422 `purchase_date_in_future`, company timezone); `warranty_expiry` not before the purchase date when both are given (422 `invalid_warranty_expiry`, B61; with no purchase date any warranty date is accepted); `cost` 0 or more, up to 2 decimals, at most 10 digits before the point (NUMERIC(12,2), the same format as a purchase line's unit cost, P2); otherwise 422 `validation_error`. | A7a; P2, B48, B61. | 2026-11-23 | 4.5 |
| I4 | **Editing manual assets** (A7a, completes A2 / F1): `PATCH /assets/{ref}` also accepts `category_id`, `purchase_date` and `cost`, but only on assets entered by hand; on a received asset they are refused with 422 `validation_error` (`details.field`), so the Slice 4.2 behaviour is unchanged. The same category, date and cost rules as on entry; `purchase_date` and `cost` can be cleared with `null`; the warranty / purchase date rule is checked on the final values, so both can be moved together. The audit row `asset.updated` holds only what changed; a category change also records the old and new category names. | A7a; A2. | 2026-11-23 | 4.5 |
| I5 | **Opening stock** (A6, A6a): `POST /stock-items/{id}/opening-stock` with `quantity` (1 to 1,000,000, as H4), optional `movement_date` (today by default, earlier allowed, future: 422 `movement_date_in_future`) and optional `note` (trimmed, up to 500: 422 `invalid_reason`; stored as the movement's reason). **Allowed once, only while the item has no movements at all** (409 `opening_stock_not_allowed`, checked after locking the item row, so two opening entries at the same moment cannot both pass); inactive item 409 `stock_item_inactive`; unknown item 404 `stock_item_not_found`. Writes an `opening` movement through `record_movement()`. Returns `{item, movement}` like issue / adjust (H7). | A6, A6a; C11, H4, H7. | 2026-11-23 | 4.5 |
| I6 | **One transaction and audit (BR-13, B39):** a manual entry writes the asset and `asset.created` (the same snapshot as receiving, with `purchase_number` empty) together; opening stock writes the movement, the new balance and a new audit action **`stock.opening`** (`before` = quantity on hand, `after` = new quantity, movement id, type, quantity, date, note) together. Any failure rolls everything back (tested by forcing the audit write to fail). `stock.opening` is added to the agreed list of audit actions. | BR-13; H5, H6. | 2026-11-23 | 4.5 |
| I7 | **No migration:** the asset's purchase link, purchase date and cost were already optional (Slice 3.2) and the `opening` movement type has existed since Slice 3.3 (P7). `alembic check` on the TEST database finds no difference between the models and the database. | Brief: "a migration only if needed". | 2026-11-23 | 4.5 |
| I8 | **Screens:** the Assets page gets **Add existing asset** (form: category (active one-by-one only; a message when there is none), name, serial, model, brand, location, purchase date (today or earlier), warranty (not before the purchase date), cost; server problems under the field; after saving, the new asset's page opens with "AST-… added."). An asset entered by hand shows an **Entered by hand** chip next to its status and, in its Purchase section, "Entered by hand (existing equipment, no purchase or vendor)" with its purchase date and cost; its history entry says "Entered by hand"; its **Edit** box also has Category, Purchase date and Cost. The stock item page gets **Enter opening stock…** only while the item is active and has no movements (the server refuses it anyway); the form has quantity, optional note and date, then a confirm box "Enter opening stock of 40 pieces for HDMI cable?" with "On hand: 0 → 40 pieces." The movement history shows **Opening stock** with the note in the Reason column. | The brief; A6a, A7. | 2026-11-23 | 4.5 |

---

## 26. Phase 5 questions answered by the owner (for Slices 5.1–5.3)

Answers to A1 and N1–N9 from `Phase4_WrapUp.md` section 3, given by the owner on 2026-11-23 (the
recommended options for all ten, accepted as written). Already fixed and unchanged: inactive
employees get no new assignments (EMP-05, BR-05); only Available assets can be assigned (BR-02,
BR-03); return and inspection are on the same form (Q5); assignments run as one transaction with an
audit row after a confirm box (build plan 5.1); old assignments are kept, never overwritten (ASN-07).

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| A1 | Employee filter on the asset register (postponed from 4.1, E1) | **Both an "Assigned to" filter and an "Assigned to" column**, added in Slice 5.1. The filter lists **active and inactive** employees, since an inactive employee may still hold an asset. | 2026-11-23 | 5.1 | Decided |
| N1 | Assignment date | **Today by default; an earlier date is allowed; a future date is refused** (company timezone), the same as A4-5a. It **cannot be before the asset was created**. | 2026-11-23 | 5.1 | Decided |
| N2 | Expected return date | **Optional.** If given, it must be **on or after the assignment date**. It **cannot be edited later** in v1: to change it, return the asset and assign it again. | 2026-11-23 | 5.1, 5.3 | Decided |
| N3 | Who can receive an asset | **Any active employee**; a login is **not** needed (Q6). Inactive employees are refused (EMP-05, BR-05). | 2026-11-23 | 5.1 | Decided |
| N4 | Return form fields (Q5) | **Return date** required: today by default, earlier allowed, **not before the assignment date**, never in the future. **Inspection outcome** required: Available, Under Maintenance or Damaged. **Condition notes** up to 1,000 characters: optional when the outcome is Available, **required when it is Damaged or Under Maintenance**. | 2026-11-23 | 5.2 | Decided |
| N5 | Returning an asset as Under Maintenance | **Status only.** Slice 5.2 sets the status and saves the notes; it does **not** open a maintenance request. When Phase 6 exists, the IT Manager opens a request separately. | 2026-11-23 | 5.2, 6.1 | Decided |
| N6 | Deactivating an employee who still holds assets | **Blocked** until the assets are returned; the message lists the assets they still hold (code `employee_has_assets`). Applies once assignments exist (Slice 5.1). | 2026-11-23 | 5.1 | Decided |
| N7 | Overdue returns | **Overdue** = an assignment whose expected return date is **before today** (company timezone) and that has **not been returned**. The overdue list is for **Admin and IT Manager only**; **no e-mail reminders** in v1 (as with warranty reminders). | 2026-11-23 | 5.3 | Decided |
| N8 | What a logged-in Employee sees | A **read-only "My assets" page** in Slice 5.3: their **current assets and past assignments**, found through the link between their login and their employee record (Q6). | 2026-11-23 | 5.3 | Decided |
| N9 | Who can assign and return | **Admin and IT Manager only** (Employee: 403), the same as every other asset action. | 2026-11-23 | 5.1, 5.2 | Decided |

---

## 27. Decisions in Slice 5.1 (✅ Slice 5.1 signed off by the owner, 2026-11-23; J1–J10 approved)

J1–J10 apply the owner's answers in section 26 (A1, N1, N2, N3, N6, N9, 2026-11-23); none of them is a
new business rule. They are technical, or follow from BR-02, BR-03, BR-05, BR-11, BR-13, EMP-05, E2,
F5, F7, H5 and Q11. **J5 confirmed by the owner (2026-11-23): keep N1 as written. All of J1–J10 were approved
with the Slice 5.1 sign-off (2026-11-23)**, after 858 backend and 221 frontend tests passed, the
migration check on the TEST database passed, and the owner's manual test in Chrome on the TEST
database.

**Review against section 26 (2026-11-23).** Every section 26 answer that applies to Slice 5.1 is covered;
the review added N9 to J2, the "return and assign again" part of N2 to J5, and which N4 checks wait for
Slice 5.2 to J1, and brought J8's example message in line with the code.

| Section 26 | Covered by | Result |
|---|---|---|
| A1: "Assigned to" filter and column; filter lists active and inactive employees | J9 (API), J10 (screens) | Matches |
| N1: today by default; earlier allowed; future refused (company timezone); not before the asset was created | J5 | Matches; owner confirmed keeping it as written |
| N2: expected return optional; on or after the assignment date; not editable later (return and assign again) | J1 (database check), J5 | Matches |
| N3: any active employee, login not needed; inactive refused | J4 | Matches |
| N4: return form fields (Slice 5.2) | J1 (columns only) | Columns ready; the checks are built in Slice 5.2 |
| N5, N7, N8: return as Under Maintenance, overdue, My assets | — | Slices 5.2 / 5.3; nothing in 5.1 |
| N6: deactivating an employee who holds assets is blocked, listing them (`employee_has_assets`) | J8, J10 | Matches |
| N9: Admin and IT Manager only (Employee 403) | J2 | Matches |
| Already fixed: EMP-05 / BR-05, BR-02 / BR-03, one transaction with audit after a confirm box, ASN-07 | J3, J4, J6, J7, J10, J1 | Matches |

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| J1 | **Data model:** migration 0014 adds the `assignments` table: asset, employee, `assignment_date`, optional `expected_return_date`, `assigned_by_user_id`, `created_at` / `updated_at` (UTC). The return fields for Slice 5.2 are already there and stay empty (`return_date`, `return_outcome` available / under_maintenance / damaged, `condition_notes` up to 1,000, `returned_at`, `returned_by_user_id`; N4). Check constraints: expected return on or after the assignment date; the required return fields are all empty or all filled; return date not before the assignment date. **Open assignment = `returned_at` empty.** The partial unique index `uq_assignments_open_asset` (on `asset_id` where `returned_at IS NULL`) allows only **one open assignment per asset** in the database. Foreign keys RESTRICT; rows never deleted (ASN-07, BR-12). New table only, no existing row changed. The rest of N4 (return date never in the future; outcome required; condition notes required for Damaged or Under Maintenance) is checked by the return action built in Slice 5.2, not by the database. Checked on the TEST database only (upgrade, downgrade, upgrade; `alembic check` clean). | Build plan 5.1; the brief ("one open assignment per asset, also in the database"; "return fields ready for 5.2"). | 2026-11-23 | 5.1 (5.2) |
| J2 | **Endpoint:** `POST /api/v1/assets/{id or asset ID}/assign` with `employee_id` (required), `assignment_date` and `expected_return_date` (both optional); any other field: 422 `validation_error`. Answers **200** with the asset (now Assigned) and its `current_assignment` (employee, assignment date, expected return, assigned by, saved at), like Retire (F5). Every asset response now carries `current_assignment` (empty unless Assigned). **Admin and IT Manager only** (N9): an Employee gets 403 `forbidden`, without a login 401 (tested). | One shape for the page to update itself; same pattern as retire; N9. | 2026-11-23 | 5.1 |
| J3 | **Only from Available** (BR-02, BR-03), each other status with its own 409 code and `details.status`: `asset_already_assigned` ("Return it first."), `asset_under_maintenance` ("Finish the repair first."), `asset_damaged`, `asset_retired` (reused from F5). | The brief asks for clear error codes per status. | 2026-11-23 | 5.1 |
| J4 | **Employee** (N3, EMP-05, BR-05): any **active** employee, with or without a login; unknown: 404 `employee_not_found`; inactive: 409 `employee_inactive` (the same codes as stock issues, H1). | N3. | 2026-11-23 | 5.1 |
| J5 | **Dates** (N1, N2): `assignment_date` defaults to today in the company timezone; earlier allowed; future: 422 `assignment_date_in_future`; before the day the asset record was created (its `created_at` converted to the company timezone): 422 `assignment_date_before_asset_created` (`details.asset_created_on`). `expected_return_date` optional; before the assignment date: 422 `invalid_expected_return_date`; equal is allowed. No way to edit it later (N2): there is no endpoint for it and `PATCH /assets` does not accept it; to change it, the asset is returned (Slice 5.2) and assigned again. **Consequence of N1, confirmed by the owner (2026-11-23):** an asset entered by hand (Slice 4.5) cannot get an assignment dated before the day it was entered, so a laptop handed out in 2024 but entered today is assigned from today. The rule is kept as written. | N1, N2 as written; owner's confirmation. | 2026-11-23 | 5.1 |
| J6 | **One transaction, two people at once** (build plan 5.1, PRD 10): the asset row is locked first (`FOR UPDATE OF assets`, as F7), the employee row share-locked; then the checks, the assignment, status Assigned and the audit row are saved together. Any failure rolls everything back (tested by forcing the audit write to fail). Two simultaneous assigns of one asset: one wins, the other gets `asset_already_assigned`, one assignment and one audit row (tested); the unique index (J1) is the final guard and gives the same error. | PRD 10; F7, H5. | 2026-11-23 | 5.1 |
| J7 | **Audit (BR-13):** new action `assignment.created` (already on the agreed list) written **on the asset** (`entity_type = assets`), so it appears in the asset's History automatically (E2): `before` `{status: available}`, `after` status, assignment id, employee id, code and name, assignment date, expected return date. | E2; BR-13. | 2026-11-23 | 5.1 |
| J8 | **Deactivating an employee who holds assets** (N6): 409 `employee_has_assets`, message "Asha Kumar (EMP-001) still holds 2 assets: AST-000001, AST-000003. Return them before deactivating this employee." ("1 asset: AST-000003. Return it …" for one) and `details.assets` (id, asset ID, name). Nothing changes (the linked login stays active too). The employee row is locked before the check, so an assignment saved at the same moment cannot slip through (it share-locks the same row, J6). Activating is unaffected. | N6. | 2026-11-23 | 5.1 |
| J9 | **Asset register** (A1): every row of `GET /assets` has `assigned_to` (employee id, code, name, status; empty unless Assigned). New filter `assigned_to=<employee id>`: assets that employee holds **now**; active or inactive employees; combines with search and the other filters; unknown employee: 404 `employee_not_found`; not a number or below 1: 422. The column is not sortable. | A1. | 2026-11-23 | 5.1 |
| J10 | **Screens:** the asset page gets **Assign…** (only for Available; greyed out with the reason otherwise: "Already assigned. Return it first.", "Under Maintenance. Finish the repair first.", "Damaged assets cannot be assigned."; not shown on a retired asset, which stays read-only, F8). It opens a form (employee picker: active employees only, with or without a login; assignment date today by default, limited to between the day the asset was added and today; optional expected return date "cannot be changed later"), then a confirm box "Assign AST-000003 to Asha Kumar (EMP-001)?" with the dates. Server refusals return to the form with the message under the field (or on top for asset status). An assigned asset shows an **Assigned to** section (employee, assignment date, expected return, assigned by and when); History shows **Assigned** · "Assigned to Asha Kumar (EMP-001) · from 20 Nov 2026 · expected back 20 Dec 2026". The Assets page gets an **Assigned to** column and an **Assigned to** filter (search-as-you-type, active and inactive employees, inactive marked), working with Clear filters and "No matches" (D9). The Employees page's deactivate box shows the `employee_has_assets` refusal with the assets listed as links, and greys out Deactivate. The shared `EmployeePicker` gains `includeInactive` and `size="small"` (existing uses unchanged). | The brief; A1, N1–N3, N6. | 2026-11-23 | 5.1 |

---

## 28. Decisions in Slice 5.2 (✅ Slice 5.2 signed off by the owner, 2026-11-24; K1–K8 approved)

K1–K8 apply the owner's answers Q5 (section 2) and N4, N5, N9 (section 26, 2026-11-23); none of them is
a new business rule. They are technical, or follow from BR-04, BR-13, ASN-07, E2, F7, J1, J3, J6 and J7.
**All of K1–K8 were approved with the Slice 5.2 sign-off (2026-11-24)**, after 902 backend and 236
frontend tests passed, `alembic check` on the TEST database found no difference (no migration), and
the return scenarios passed in the browser on the TEST database (Available, Under Maintenance and
Damaged returns; notes, date and outcome refusals; deactivation blocked while holding assets and
allowed after returning them).

| Section 2 / 26 | Covered by | Result |
|---|---|---|
| Q5: return and inspection on the same form | K1, K8 | Matches |
| N4: return date required, today by default, earlier allowed, not before the assignment date, never future; outcome required (Available / Under Maintenance / Damaged); notes up to 1,000, optional for Available, required for Damaged or Under Maintenance | K2, K3 | Matches |
| N5: Under Maintenance on return sets the status only; no maintenance request | K4 | Matches |
| N9: Admin and IT Manager only (Employee 403) | K1 | Matches |
| ASN-07 groundwork: the closed assignment is kept, never overwritten | K5 | Matches |
| BR-13 / coverage gap 1 (section 1): returns are audited | K6 | Resolved for returns |

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| K1 | **Endpoint:** `POST /api/v1/assets/{id or asset ID}/return` with `inspection_outcome` (required), `return_date` and `condition_notes` (optional); any other field: 422 `validation_error`. Answers **200** with the asset (new status, `current_assignment` empty), like Assign (J2). **Admin and IT Manager only** (N9): Employee 403 `forbidden`, no login 401. | One shape for the page to update itself; N9. | 2026-11-23 | 5.2 |
| K2 | **Return date** (N4): defaults to today in the company timezone when left out (the form always sends it, starting at today); earlier allowed; future: 422 `return_date_in_future`; before the assignment date: 422 `return_date_before_assignment` (`details.assignment_date`); the same day as the assignment is allowed. | N4; same pattern as the assignment date (J5). | 2026-11-23 | 5.2 |
| K3 | **Outcome and notes** (N4): outcome must be `available`, `under_maintenance` or `damaged` (missing or anything else: 422 `invalid_inspection_outcome`); it becomes the asset's status. Notes trimmed, up to 1,000 characters (422 `invalid_condition_notes`); empty or spaces only with Damaged or Under Maintenance: 422 `condition_notes_required`; with Available they are optional and kept if given. | N4. | 2026-11-23 | 5.2 |
| K4 | **Under Maintenance sets the status only** (N5): no maintenance request is created; the confirm box says so. After a Damaged or Under Maintenance return the asset cannot be assigned (J3: `asset_damaged` / `asset_under_maintenance`); after an Available return it can be assigned again (a new assignment row). | N5; BR-02, BR-03. | 2026-11-23 | 5.2 (6.x) |
| K5 | **The assignment is closed, never overwritten or deleted** (ASN-07 groundwork for 5.3): the open row gets `return_date`, `return_outcome`, `condition_notes`, `returned_at` (database time) and `returned_by_user_id`; its employee, assignment date and expected return stay as they were. An asset's assignments therefore form its full holder history. **No migration:** the 5.1 table (J1) already had these columns and their checks. | J1; ASN-07. | 2026-11-23 | 5.2 (5.3) |
| K6 | **One transaction and audit** (BR-13; closes coverage gap 1 for returns): new audit row `assignment.returned` (already on the agreed list) on the asset, so it shows in the asset's History (E2): `before` `{status: assigned}`, `after` new status, assignment id, employee id, code and name, assignment date, return date, outcome, notes. Saved together with the assignment and status; any failure saves nothing (tested by forcing the audit write to fail). | BR-13; J7. | 2026-11-23 | 5.2 |
| K7 | **Only an assigned asset; two returns at once** (PRD 10): the asset row is locked first (as F7 / J6), then its open assignment row. An asset that is not Assigned (or has no open assignment): 409 `asset_not_assigned` (`details.status`), which is also what the second of two simultaneous returns gets (tested: one wins, one closed assignment, one audit row). A holder who is now inactive can still return the asset (returning is how N6 is cleared). | PRD 10; J6; N6. | 2026-11-23 | 5.2 |
| K8 | **Screens:** the asset page gets **Return…** (shown only while the asset is Assigned; the greyed-out Assign… stays beside it). It opens one form (Q5): "Held by Asha Kumar (EMP-001) since …", return date (today by default, limited to between the assignment date and today), inspection outcome (Available / Under Maintenance / Damaged) and condition notes with a 0 / 1,000 counter, marked required (and "required for this outcome") when the outcome is not Available. Then a confirm box "Return AST-000003 as Damaged?" with the holder, the assignment and return dates, the new status and the notes (and, for Under Maintenance, "This sets the status only; no maintenance request is opened."). Server refusals return to the form with the message under the field (on top for `asset_not_assigned`). After saving: "AST-000003 returned. Status: Damaged.", the new status, no "Assigned to" section, and History shows **Returned** · "Returned by Asha Kumar — Damaged: screen cracked". | The brief; Q5, N4, N5. | 2026-11-23 | 5.2 |

---

## 29. Phase 5 questions answered by the owner (for Slice 5.3)

Six points not covered by section 26, raised with the Slice 5.3 plan and answered by the owner on
2026-11-24 (the recommended options, accepted as written). Already fixed and unchanged: N2 (expected
return date, not editable), N7 (overdue = expected return before today, company timezone, not returned;
Admin and IT Manager only; no e-mail reminders), N8 (read-only My Assets page for Employees in 5.3).

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| N10 | Where does the overdue list go? | **On the existing "Assignments" menu page** (Admin and IT Manager), showing only the overdue list for now. | 2026-11-24 | 5.3 | Decided |
| N11 | Where does an Employee land after login? | **On My Assets until Slice 6.4 builds My Dashboard.** | 2026-11-24 | 5.3 (6.4) | Decided |
| N12 | What may an Employee see in their past assignments? | **Asset, assignment date, expected return, return date and inspection outcome.** Not the condition notes and not the staff e-mails (who assigned or returned it). | 2026-11-24 | 5.3 | Decided |
| N13 | Can Admin or IT Manager open My Assets? | **No.** My Assets is for the Employee role only; staff use the employee page. | 2026-11-24 | 5.3 | Decided |
| N14 | A separate assignment history table on the asset page? | **No, not in 5.3.** The asset's History already lists every assign and return. | 2026-11-24 | 5.3 | Decided |
| N15 | The build plan puts My Assets in 6.4; N8 puts it in 5.3. | **Build My Assets in 5.3** (N8, the newer owner decision). Slice 6.4 still adds My Dashboard and My Requests. | 2026-11-24 | 5.3, 6.4 | Decided |

---

## 30. Decisions in Slice 5.3 (✅ Slice 5.3 signed off by the owner, 2026-11-24; L1–L8 approved)

L1–L8 apply the owner's answers N2, N7, N8 (section 26) and N10–N15 (section 29); none of them is a new
business rule. They are technical, or follow from ASN-07, ASN-08, EMP-04, PRD 4.1 / 4.2, Q11, J1, K5 and
order fix b. **✅ Signed off by the owner on 2026-11-24**, after the full test run (924 backend, 246 frontend) and the browser checks on the TEST database passed.

| Owner's answer | Covered by | Result |
|---|---|---|
| ASN-07: old assignments kept, never overwritten | L1 | Matches (already true since J1 / K5; now shown) |
| EMP-04: an employee's current assets and history for authorized users | L2, L8 | Matches |
| N7 / ASN-08: overdue = expected return before today (company timezone), not returned; staff only; no e-mails | L3, L4, L8 | Matches |
| N2: expected return date not editable | L3 | Unchanged (overdue only reads it) |
| N8, N12, N13: read-only My Assets for Employees; no notes or staff e-mails; staff cannot open it | L5, L8 | Matches |
| N10: overdue list on the Assignments page | L8 | Matches |
| N11: Employees land on My Assets until 6.4 | L8 | Matches |
| N14: no separate assignment table on the asset page | L8 | Matches (only an Overdue badge added) |
| N15: My Assets built in 5.3; 6.4 still adds My Dashboard and My Requests | L8 | Matches |

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| L1 | **No migration, read-only slice:** history and overdue are read from the `assignments` table (J1), where every assignment is its own row and a return only fills its return fields (K5). Nothing in 5.3 changes data, so nothing writes an audit row (tested: reading leaves the rows and the audit log unchanged). | ASN-07; BR-13 covers changes, not reads. | 2026-11-24 | 5.3 |
| L2 | **Employee history:** `GET /api/v1/employees/{id}/assignments` (Admin and IT Manager) returns `employee`, `current` (still held, oldest assignment first) and `past` (returned, newest return first). Each row: asset (ID, name, serial, status now), employee, assignment date, expected return, return date, outcome, condition notes, assigned by / when, returned by / when, `is_open`, `is_overdue`, `days_overdue`. Inactive employees included; unknown: 404 `employee_not_found`. Not paged (one person's assignments stay few). | EMP-04, ASN-07. | 2026-11-24 | 5.3 |
| L3 | **Overdue rule (N7)** in one place (`days_overdue()`): open, has an expected return date, and that date is **before today** in the company timezone (the same "today" as every other date rule, Q11). Due today is not overdue; no expected date is never overdue; a returned assignment is never overdue, even if returned late. `days_overdue` = today minus the expected return date. | N7; Q11. | 2026-11-24 | 5.3 |
| L4 | **Overdue list:** `GET /api/v1/assignments/overdue` (Admin and IT Manager; Employee 403), paged, most late first (expected return date ascending), sortable by `expected_return_date`, `assignment_date`, `asset_code`, `employee`; `search` matches part of the asset ID, asset name, serial number, employee ID or name (any case). No e-mail reminders (N7). Asset responses' `current_assignment` gains `is_overdue`. | ASN-08, N7, N10. | 2026-11-24 | 5.3 |
| L5 | **My Assets:** `GET /api/v1/me/assignments`, **Employee role only** (Admin and IT Manager: 403, N13). The employee comes from the login's link (order fix b); a login without one: 404 `employee_not_linked`. Same current / past split, but each row has only the asset, assignment date, expected return, return date, outcome, `is_open`, `is_overdue`, `days_overdue`: **no condition notes, no staff e-mails, no other employee** (N12, PRD 4.1; tested). | N8, N12, N13; PRD 4.1, 4.2. | 2026-11-24 | 5.3 |
| L6 | **Who sees what (PRD 4.1):** the staff endpoints answer 403 to an Employee (they cannot read another employee's history or the overdue list); without a login every endpoint answers 401 (tested). | PRD 4.1; N9 pattern. | 2026-11-24 | 5.3 |
| L7 | **Build plan alignment (N15):** My Assets moves from Slice 6.4 to 5.3; Slice 6.4 still builds My Dashboard and My Requests, and the Employee home page moves to My Dashboard then (N11). | N11, N15. | 2026-11-24 | 5.3 (6.4) |
| L8 | **Screens:** **Employee page** `/employees/:id` (opened from the name on the Employees list): details (department, designation, email, phone, login), **Current assets** (asset ID linking to the asset page, serial, assigned on, expected return with a red "N days overdue" badge, assigned by) and **Past assignments** (asset, assigned on, expected return, returned on, inspection outcome, condition notes, returned by), with "No assets held now." / "No past assignments." when empty. **Assignments** menu page (N10) = **Overdue returns**: asset ID, asset, employee (inactive marked), assigned on, expected return, "N days overdue"; search, sort, paging, "No overdue returns"; a row opens the asset page to record the return. **My Assets** `/my/assets` (Employee): the same two tables without notes, staff e-mails or links, and no buttons; Employees land here after login (N11). The asset page's "Assigned to" section shows a red **Overdue** badge next to the expected return. Shared component `AssignmentTables.jsx`. | The plan approved by the owner (2026-11-24); N10–N15. | 2026-11-24 | 5.3 |

---

## 31. Phase 6 questions answered by the owner (for Slice 6.1)

Fourteen points raised with the Slice 6.1 plan and answered by the owner on 2026-11-24 (the
recommended options for all fourteen, accepted as written). Already fixed and unchanged: Q9 (the
asset becomes Under Maintenance only when the IT Manager sets the request to In Progress, Slice 6.2;
reporting never changes the asset's status), Q10 (priority Low / Medium / High, optional, set by the
IT Manager), Q13 (no technician role; the IT Manager owns maintenance, Admin can do the same), N5
(a return as Under Maintenance opens no request; the IT Manager opens one separately), N11 / N15
(Employees land on My Assets; My Requests and My Dashboard are Slice 6.4).

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| O1 | Which asset statuses allow a request (staff)? | **Available, Assigned, Damaged and Under Maintenance** (Under Maintenance is needed for N5). **Retired: refused** (`asset_retired`; a retired asset is read-only, A3 / F8). | 2026-11-24 | 6.1 | Decided |
| O2 | More than one open request per asset? | **No.** One open request (Reported or In Progress) per asset, also enforced in the database; the refusal names the open request. Completed and Cancelled requests do not block a new one. Slice 6.3 may revisit what "open" means once inspection exists. | 2026-11-24 | 6.1 (6.2, 6.3) | Decided (revised by T4, section 35) |
| O3 | Which assets can an Employee report on? | Only an asset they **hold right now** (an open assignment to the employee record linked to their login). | 2026-11-24 | 6.1 | Decided |
| O4 | Issue text | **Required**, trimmed, **up to 1,000 characters** (same as condition notes, N4). | 2026-11-24 | 6.1 | Decided |
| O5 | Reported date | **Staff:** today by default; an earlier date is allowed; never in the future; not before the asset was created (as N1). **Employee:** always today, set by the server. | 2026-11-24 | 6.1 | Decided |
| O6 | Employee after returning the asset | **Cannot report it any more.** Requests they already made stay theirs to follow in Slice 6.4. | 2026-11-24 | 6.1 (6.4) | Decided |
| O7 | Employee picks an asset that is not theirs | **404 `asset_not_found`**, the same answer as for a missing asset, so other people's assets cannot be discovered (PRD 4.1). | 2026-11-24 | 6.1 | Decided |
| O8 | Priority on Employee reports | The Employee cannot set it (Q10). **In 6.1 staff set priority only when they create a request.** Changing priority on an existing request (including an Employee's) comes with the Slice 6.2 review screen. | 2026-11-24 | 6.1 (6.2) | Decided |
| O9 | "Reported on behalf of employee X"? | **No.** The PRD has no such field; the reporter is always the logged-in user. | 2026-11-24 | 6.1 | Decided |
| O10 | Confirm box before submitting? | **No.** Reporting changes no status and is not in Slice 8.2's confirm-box list; the form's Submit is enough. | 2026-11-24 | 6.1 | Decided |
| O11 | Request numbering | **MNT-000001, MNT-000002, …** from a database sequence (like PUR, B42, and AST, Q3). | 2026-11-24 | 6.1 | Decided |
| O12 | Where requests appear in 6.1 | **Asset page:** a "Maintenance requests" section and the History entry. **Maintenance menu page:** a simple staff list (search, status filter, paging; no "new request" button, staff start from the asset page). **Employee:** the success message and a "Problem reported (MNT-…)" note on the My Assets row; the full My Requests page is Slice 6.4. | 2026-11-24 | 6.1 (6.4) | Decided |
| O13 | Notifications / e-mail to the IT Manager? | **No** (as N7: no e-mails in v1). | 2026-11-24 | 6.1 | Decided |
| O14 | Audit action | A new **`maintenance.reported`**, written **on the asset** (so it shows in the asset's History, E2), added to the agreed action list. | 2026-11-24 | 6.1 | Decided |

---

## 32. Decisions in Slice 6.1 (✅ Slice 6.1 signed off by the owner, 2026-11-25; M1–M8 approved)

M1–M8 apply Q9, Q10, Q13, N5 and the owner's answers O1–O14 (section 31); none of them is a new
business rule. They are technical, or follow from BR-12, BR-13, PRD 4.1, E2, F7, J1, J6, L5 and Q11.
**All of M1–M8 were approved with the Slice 6.1 sign-off (2026-11-25)**, after 986 backend and 262
frontend tests passed, the production build succeeded, migration 0015 was checked on the TEST database
(upgrade, downgrade, upgrade; `alembic check` clean) and the browser check on the TEST database passed
as IT Manager, Admin and Employee.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| M1 | **Data model:** migration 0015 adds the `maintenance_requests` table: `request_number` (MNT-000001… from the sequence `maintenance_request_number_seq`, O11), `asset_id` (FK assets, RESTRICT), `issue_description` (up to 1,000, not blank, O4), `priority` (empty or `low` / `medium` / `high`, Q10), `status` (`reported` / `in_progress` / `completed` / `cancelled`, MNT-04; 6.1 writes only `reported`), `reported_date` (business date), `reported_by_user_id` (FK users, RESTRICT), `created_at` / `updated_at` (UTC). The partial unique index `uq_maintenance_requests_open_asset` (on `asset_id` where status is `reported` or `in_progress`) allows only **one open request per asset** (O2). Repair notes, provider, cost and completion date are added by Slice 6.2. New table only, no existing row changed; never deleted (BR-12). Checked on the TEST database only (upgrade, downgrade, upgrade; `alembic check` clean). | MNT-03, MNT-04; O2, O11. | 2026-11-24 | 6.1 (6.2) |
| M2 | **Staff endpoint:** `POST /api/v1/assets/{id or asset ID}/maintenance-requests` (201) with `issue_description` (required), `priority` (optional) and `reported_date` (optional); any other field: 422 `validation_error`. **Admin and IT Manager only** (Q13): Employee 403, no login 401. | MNT-02; Q10, Q13. | 2026-11-24 | 6.1 |
| M3 | **Employee endpoint:** `POST /api/v1/me/maintenance-requests` (201) with `asset_id` and `issue_description` only; a priority, a date or any other field: 422 `validation_error` (Q10, O5, O8). **Employee role only** (staff 403). The asset must be held by the employee linked to the login **now** (open assignment, O3, O6); anything else, including a missing asset, another employee's asset or an asset they returned: **404 `asset_not_found`** (O7). Login not linked: 404 `employee_not_linked` (as L5). Reported date = today (company timezone). | MNT-01; O3, O5–O8; PRD 4.1. | 2026-11-24 | 6.1 |
| M4 | **Checks (both endpoints):** issue trimmed, required, up to 1,000 (422 `invalid_issue_description`); retired asset 409 `asset_retired` (O1); an open request already exists: 409 `maintenance_request_open` with `details.request_number` (O2); staff reported date in the future 422 `reported_date_in_future`, before the asset was created 422 `reported_date_before_asset_created` (`details.asset_created_on`, O5). **The asset's status is never changed** (Q9). | O1, O2, O4, O5; Q9. | 2026-11-24 | 6.1 |
| M5 | **One transaction, two people at once:** the asset row is locked first (as F7 / J6); then the checks, the request and the audit row are saved together; any failure saves nothing (tested by forcing the audit write to fail). Two reports on one asset at the same moment: one wins, the other gets `maintenance_request_open`; the partial unique index (M1) is the final guard and gives the same error. | PRD 10; F7, J6. | 2026-11-24 | 6.1 |
| M6 | **Audit (BR-13, O14):** new action `maintenance.reported` written **on the asset** (`entity_type = assets`), so it shows in the asset's History (E2): `after` = request id and number, issue, priority, reported date, status `reported` and the reporter's role. No `before` (the asset's status does not change). `maintenance.status_changed` stays reserved for Slice 6.2. | BR-13; E2; O14. | 2026-11-24 | 6.1 |
| M7 | **Reading (O12):** `GET /api/v1/assets/{ref}/maintenance-requests` (staff; the asset's requests, newest first, not paged) and `GET /api/v1/maintenance-requests` (staff; paged, newest first; `search` matches part of the request number, asset ID, asset name or serial number; `status` filter; sort by `request_number`, `reported_date`, `priority`, `status`, `asset_code`). Each request: number, asset (id, asset ID, name, serial, status), issue, priority, status, reported date, reported by (email, role), saved at. `GET /me/assignments` rows gain `open_request` (number and status of the asset's open request while the row is still held, else empty) for the My Assets note; nothing else is added for Employees (My Requests is Slice 6.4). | O12; MNT-06 groundwork. | 2026-11-24 | 6.1 (6.2, 6.4) |
| M8 | **Screens:** the asset page gets **Report a problem…** (not shown on Retired assets; greyed out with "MNT-… is already open." while a request is open) opening a form: issue with a 0 / 1,000 counter, priority (None / Low / Medium / High) and reported date (today by default, between the day the asset was added and today); no confirm box (O10). Afterwards "MNT-000001 reported." and a **Maintenance requests** section (number, reported on, by, priority, status, issue). History shows **Problem reported** · "MNT-000001 · High · screen flickers". **Maintenance** menu page (staff): the request list with search, status filter, paging and "No maintenance requests"; a row opens the asset page. **My Assets** (Employee): each current asset gets **Report a problem** (issue only), then "Problem reported: MNT-000001. The IT team will review it."; a row with an open request shows "Problem reported (MNT-…)" instead of the button. | O10, O12. | 2026-11-24 | 6.1 |

---

## 33. Phase 6 questions answered by the owner (for Slice 6.2)

Fourteen points raised with the Slice 6.2 plan and answered by the owner on 2026-11-25 (the
recommended options for all fourteen, accepted as written). Already fixed and unchanged: Q9 (the asset
becomes Under Maintenance when the IT Manager sets In Progress), Q10 / O8 (priority optional, set by the
IT Manager), Q13 (Admin and IT Manager own maintenance), O2 (one open request per asset; open = Reported
or In Progress), J3 (an Under Maintenance asset cannot be assigned, BR-05), A3 (an Under Maintenance asset
cannot be retired), K7 (only an Assigned asset can be returned), E2 (an asset's history is its audit log
rows), BR-13 / coverage gap 1 (status changes audited in the same transaction), build plan 6.3 (a completed
repair does not make the asset Available until it passes inspection).

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| S1 | The asset is Assigned when work starts | **Return it first.** Start work is refused ("Return it first.") while the asset is Assigned; the return form can already set Under Maintenance (N5). Keeping the assignment would leave an Under Maintenance asset that cannot be returned (K7) and a holder who cannot be deactivated (N6). | 2026-11-25 | 6.2 | Decided |
| S2 | Asset status when a request is Cancelled while In Progress | **Stays Under Maintenance until the Slice 6.3 inspection**, the same as Completed, so an asset never becomes Available without inspection (MNT-07). Cancelling a Reported request leaves the asset's status unchanged. | 2026-11-25 | 6.2 (6.3) | Decided |
| S3 | Reported → Completed directly? | **No.** Work must be started first (asset Under Maintenance, full history). | 2026-11-25 | 6.2 | Decided |
| S4 | Reopening Completed or Cancelled requests? | **No, they are final.** A new request is opened instead (O2 allows it). | 2026-11-25 | 6.2 | Decided |
| S5 | Fields required at Completed | **Completion date and repair notes required**; service provider and cost optional ("where applicable", MNT-05). | 2026-11-25 | 6.2 | Decided |
| S6 | Cost | Optional, INR, **0 or more with 2 decimals**, at most 10 digits before the point (as P2 / I3). Can be entered while In Progress or at Completed and changed until the request is closed. | 2026-11-25 | 6.2 | Decided |
| S7 | Completion date | Today by default; **earlier allowed; never in the future; not before the start date** (company timezone). | 2026-11-25 | 6.2 | Decided |
| S8 | Start date | A **work started date** is recorded: today by default; earlier allowed; never in the future; not before the reported date. | 2026-11-25 | 6.2 | Decided |
| S9 | Service provider / responsible person | **One optional text field** (up to 200) for an outside company or a staff member's name; set at Start, at Completed or with Edit details. | 2026-11-25 | 6.2 | Decided |
| S10 | Changing priority | **Admin and IT Manager, while Reported or In Progress**, recorded in the history; locked once the request is closed. | 2026-11-25 | 6.2 | Decided |
| S11 | Who may cancel, and the reason | **Admin and IT Manager only**, from Reported or In Progress, with a **required reason up to 500** characters (as A3). An Employee cannot cancel their own report in v1. | 2026-11-25 | 6.2 | Decided |
| S12 | Repair notes | **One repair notes field up to 1,000** (as N4), editable while the request is open; each change kept in the history. No separate running log of notes. | 2026-11-25 | 6.2 | Decided |
| S13 | Where the maintenance history lives | The **audit log rows on the asset** (as E2), no new history table. The request page shows the rows of that request. | 2026-11-25 | 6.2 | Decided |
| S14 | Retiring an asset with an open request | **Blocked while any request is open** ("Cancel or finish MNT-… first."). New rule, decided by the owner. | 2026-11-25 | 6.2 (4.2 retire) | Decided |

---

## 34. Decisions in Slice 6.2 (✅ Slice 6.2 signed off by the owner, 2026-11-25; U1–U9 approved)

U1–U9 apply Q9, Q10, Q13, O2, J3, A3, K7, E2, BR-05, BR-13 and the owner's answers S1–S14 (section 33);
S14 is the only new business rule, decided by the owner. The rest are technical. **Coverage gap 1
(section 1) is resolved for maintenance:** every status change and every detail change is audited in
the same transaction (U6). **All of U1–U9 were approved with the Slice 6.2 sign-off (2026-11-25)**, after
277 frontend tests passed and the production build succeeded; the full backend run passed 1,034 tests, its
6 failures (a Slice 6.1 test-only shortcut that the new check constraints correctly refused) were fixed and
both maintenance test files then passed (116); migration 0016 was checked on the TEST database (upgrade,
downgrade, upgrade; `alembic check` clean) and the browser check on the TEST database passed as IT Manager
and Admin.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| U1 | **Data model:** migration 0016 adds to `maintenance_requests`: `started_date`, `started_at`, `started_by_user_id`; `service_provider` (up to 200), `repair_notes` (up to 1,000), `cost` (NUMERIC(12,2), 0 or more); `completion_date`, `completed_at`, `completed_by_user_id`; `cancelled_at`, `cancelled_by_user_id`, `cancel_reason` (up to 500). Check constraints: the start fields are filled together and only once work started (In Progress, Completed, or Cancelled after start); the completion fields together and only when Completed (with repair notes); the cancel fields together and only when Cancelled; completion date not before the start date; start date not before the reported date. All new columns may be empty, so existing rows stay valid; no existing row is changed. Checked on the TEST database only (upgrade, downgrade, upgrade; `alembic check` clean). | MNT-04, MNT-05; S5–S9, S11, S12. | 2026-11-25 | 6.2 |
| U2 | **Endpoints** (Admin and IT Manager; Employee 403, no login 401; `{ref}` = id or MNT number): `GET /maintenance-requests/{ref}` (one request with its history), `POST …/{ref}/start` (`started_date` optional, `service_provider` optional), `POST …/{ref}/complete` (`completion_date` optional = today, `repair_notes` required, `service_provider` and `cost` optional), `POST …/{ref}/cancel` (`reason` required), `PATCH …/{ref}` (`priority`, `service_provider`, `repair_notes`, `cost`; `null` clears; only while open). Unknown request: 404 `maintenance_request_not_found`; any other field: 422 `validation_error`. Each answers 200 with the request. | MNT-04, MNT-05; Q13; S5–S12. | 2026-11-25 | 6.2 |
| U3 | **Status moves:** Reported → In Progress (asset becomes **Under Maintenance**, Q9); In Progress → Completed (asset **stays Under Maintenance** until the 6.3 inspection); Reported → Cancelled (asset unchanged); In Progress → Cancelled (asset **stays Under Maintenance**, S2). Everything else (Reported → Completed, any move from Completed or Cancelled) is 409 `invalid_status_change` with `details.from` / `details.to` (S3, S4). Start work on an **Assigned** asset: 409 `asset_assigned` ("Return it first.", S1); on a Retired asset: 409 `asset_retired`. Start from Available, Damaged or Under Maintenance. | Q9, BR-05, MNT-07; S1–S4. | 2026-11-25 | 6.2 (6.3) |
| U4 | **Field rules:** start date today by default, earlier allowed, future 422 `started_date_in_future`, before the reported date 422 `started_date_before_reported` (S8); completion date today by default, future 422 `completion_date_in_future`, before the start date 422 `completion_date_before_start` (S7); repair notes trimmed, up to 1,000, required at Completed (422 `invalid_repair_notes`, S5, S12); service provider trimmed, up to 200 (422 `invalid_service_provider`, S9); cost 0 or more, 2 decimals, NUMERIC(12,2) (422 `validation_error`, S6), always saved and audited with 2 decimals (300 → 300.00); cancel reason trimmed, required, up to 500 (422 `invalid_cancel_reason`, S11); priority low / medium / high or `null` (S10). Edits on a closed request: 409 `maintenance_request_closed`. An edit that changes nothing saves nothing and writes no audit row (as B16). | S5–S12. | 2026-11-25 | 6.2 |
| U5 | **One transaction, two people at once:** every action locks the asset row first, then the request row (always in that order, as F7 / J6), re-reads both, checks, saves the request, the asset's status and the audit row together; a failure saves nothing (tested by forcing the audit write to fail). Two actions on the same request at the same moment: one wins, the other gets `invalid_status_change` (tested). | PRD 10; F7, J6. | 2026-11-25 | 6.2 |
| U6 | **Audit and history (BR-13, coverage gap 1, MNT-06, S13):** `maintenance.status_changed` (already on the agreed list) for start, complete and cancel, and a new `maintenance.updated` for priority and detail edits, both written **on the asset** so they show in its History (E2). `before` / `after` hold the request status and, when it changes, the asset status, plus the details entered (start date and provider; completion date, notes, provider, cost; cancel reason; or the old and new values of each edited field), with the request id and number. The request page's history = the asset's audit rows whose `request_id` is this request. No new history table. | BR-13; E2; S13. | 2026-11-25 | 6.2 |
| U7 | **Retiring with an open request** (S14): `POST /assets/{ref}/retire` on an asset with a Reported or In Progress request: 409 `asset_has_open_request` ("Cancel or finish MNT-… first.", `details.request_number`). Checked after the asset row is locked. The asset page greys out Retire… with that reason. | S14. | 2026-11-25 | 6.2 (4.2) |
| U8 | **BR-05 / MNT-07 unchanged and tested:** an In Progress (or Completed / Cancelled-after-start) asset is Under Maintenance, so Assign… is refused with the existing `asset_under_maintenance` (J3); the asset stays Under Maintenance until Slice 6.3's inspection. | BR-05, MNT-07; J3. | 2026-11-25 | 6.2 (6.3) |
| U9 | **Screens:** a **request page** `/maintenance/:requestRef` (Admin and IT Manager): asset link, issue, priority, status, reported / started / completed or cancelled (who, when), service provider, repair notes, cost, and the request's **History**. Buttons by status: **Start work…** (Reported; greyed out "Return it first." while the asset is Assigned), **Mark completed…** (In Progress), **Cancel request…** (Reported or In Progress), **Edit details** (while open: priority, provider, notes, cost). Each status button opens a form, then a confirm box: Start "AST-… becomes Under Maintenance and cannot be assigned until it is inspected."; Complete "AST-… stays Under Maintenance until it is inspected."; Cancel "This cannot be undone." (plus the asset note when work had started). The Maintenance list's rows now open the **request page** (changes O12's "row opens the asset page"); the asset page's request numbers link to it; the asset's History shows "Work started · MNT-000001 · Reported → In Progress · asset Under Maintenance", "Completed · …", "Cancelled · Reason: …", "Request edited · Priority: Low → High". | S1–S14; the plan approved by the owner. | 2026-11-25 | 6.2 |


---

## 35. Phase 6 questions answered by the owner (for Slice 6.3)

Twelve points raised with the Slice 6.3 plan and answered by the owner on 2026-11-26 (the recommended
options for all twelve, accepted as written). Already fixed and unchanged: PRD MNT-07 and workflow 7.4 (after
completion the asset is inspected; Available only if fit for use, otherwise Damaged or Retired), U3 / S2 (a
Completed request, or one Cancelled while In Progress, leaves the asset Under Maintenance until this
inspection), S4 (Completed and Cancelled requests are final), N4 / K3 (the return's inspection: outcome plus
condition notes up to 1,000, required unless Available), F2 / F6 (the retirement record on the asset and the
`asset.retired` audit row), Q13 / N9 (Admin and IT Manager own maintenance), E2 / S13 (an asset's history is
its audit log rows). **Two earlier rules are revised by the owner here: O2 (answer T4) and A3 (answer T7).**

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| T1 | A separate step, or part of Mark completed? | **A separate step.** Completion is already recorded (S5); the repair and the check can be on different days. | 2026-11-26 | 6.3 | Decided |
| T2 | Which requests can be inspected? | **Completed, and Cancelled after work started** (S2 sends those assets here). A request cancelled before work started never changed the asset, so it needs no inspection. | 2026-11-26 | 6.3 | Decided |
| T3 | Outcomes | **Available, Damaged or Retired** (build plan 6.3). No "needs more repair / stays Under Maintenance" outcome: Damaged covers "not fit", and a new request takes it back into repair. | 2026-11-26 | 6.3 | Decided |
| T4 | Does a request awaiting inspection count as open (revises O2)? | **Yes.** While a request awaits inspection no new request can be reported for the asset; the refusal names the request. | 2026-11-26 | 6.3 (6.1 report) | Decided |
| T5 | Notes | **Reuse the return's wording and limit:** "Condition notes", up to 1,000; optional for Available, required for Damaged and Retired. | 2026-11-26 | 6.3 | Decided |
| T6 | Retired: the reason | **The required notes are the retirement reason**, so at most 500 characters for Retired (A3). The confirm box says it is permanent. The asset gets the same retirement record and `asset.retired` row as Retire…. | 2026-11-26 | 6.3 (4.2) | Decided |
| T7 | Retiring from Under Maintenance (revises A3) | **Allowed only through this inspection.** The Retire… button keeps its rule (Available or Damaged only). | 2026-11-26 | 6.3 (4.2) | Decided |
| T8 | Inspection date | **Today by default; earlier allowed; not before the completion date** (for a request cancelled during repair, not before the day it was cancelled); **never in the future** (company timezone). | 2026-11-26 | 6.3 | Decided |
| T9 | Can an inspection be changed afterwards? | **No, it is final** (as returns and S4). A wrong Available is put right by reporting a new problem. | 2026-11-26 | 6.3 | Decided |
| T10 | Who can inspect? | **Admin and IT Manager** (Q13, N9). | 2026-11-26 | 6.3 | Decided |
| T11 | Where is the Inspect… button? | **On the request page and the asset page**, opening the same form. | 2026-11-26 | 6.3 | Decided |
| T12 | Assets Under Maintenance from a return, without a request (N5) | **No inspection without a request.** Staff report a problem, start work, complete it and inspect, so every repair has a record. | 2026-11-26 | 6.3 | Decided |

---

## 36. Decisions in Slice 6.3 (✅ Slice 6.3 signed off by the owner, 2026-11-26; V1–V9 approved)

V1–V9 apply MNT-07, workflow 7.4, BR-05, BR-13 and the owner's answers T1–T12 (section 35). T4 (revises O2)
and T7 (revises A3) are the only rule changes, both decided by the owner. The rest are technical. **All of
V1–V9 were approved with the Slice 6.3 sign-off (2026-11-26)**, after the full backend run passed 1,077
tests, 291 frontend tests passed and the production build succeeded; migration 0017 was checked on the
TEST database (upgrade, downgrade, upgrade; `alembic check` clean) and the browser check on the TEST
database passed as IT Manager (MNT-000001 inspected as Available; AST-000004 became Available).

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| V1 | **Data model:** migration 0017 adds to `maintenance_requests`: `inspection_outcome` (`available` / `damaged` / `retired`), `inspection_date`, `inspection_notes` (up to 1,000), `inspected_at` (database time) and `inspected_by_user_id` (FK users, RESTRICT). All nullable, no backfill, no existing row changed. Check constraints: the five are filled together (notes may be empty); only a Completed request, or a Cancelled one with a start, can carry an inspection; the outcome is one of the three; notes required unless Available; inspection date not before the completion date. The request's **status does not change** (it stays Completed or Cancelled); "awaiting inspection" = work started, Completed or Cancelled, not yet inspected. | T2, T5, T9; the database guards the rules as in U1. | 2026-11-26 | 6.3 |
| V2 | **One blocking request per asset** (T4): the partial unique index `uq_maintenance_requests_open_asset` is rebuilt to cover `status = 'reported' OR (started_at IS NOT NULL AND inspected_at IS NULL)` (Reported, In Progress, awaiting inspection). Reporting while a request awaits inspection: 409 `maintenance_request_awaiting_inspection` (`details.request_number`, "MNT-… is awaiting inspection for AST-…. Inspect the asset first."). `maintenance_request_open` keeps its meaning (Reported or In Progress), and so does S14 (retire blocked only by an open request; an asset awaiting inspection is Under Maintenance and not retirable anyway). | T4. | 2026-11-26 | 6.3 (6.1) |
| V3 | **Endpoint:** `POST /api/v1/maintenance-requests/{ref}/inspect` with `inspection_outcome` (required), `inspection_date` and `condition_notes` (optional), the return's field names (K1); any other field: 422 `validation_error`. Answers **200** with the request and its history (as U2). Admin and IT Manager only: Employee 403, no login 401. Every request response gains `awaiting_inspection` and the inspection fields (`inspected_by` as email and role). The list's `status` filter also takes `awaiting_inspection`. | T10; one shape for the pages (U2). | 2026-11-26 | 6.3 |
| V4 | **Checks and errors:** not awaiting inspection (Reported, In Progress, cancelled before work started, already inspected): 409 `request_not_awaiting_inspection` (`details.status`, a message for each case); the asset not Under Maintenance (a safety net; cannot happen through the app): 409 `asset_not_under_maintenance`; outcome missing or not one of the three: 422 `invalid_inspection_outcome`; notes over 1,000: 422 `invalid_condition_notes`; missing or blank for Damaged or Retired: 422 `condition_notes_required`; over 500 for Retired: 422 `invalid_retire_reason`; date in the future: 422 `inspection_date_in_future`; before the completion date (or the day it was cancelled, company timezone): 422 `inspection_date_before_completion` (`details.earliest_date`). Notes are trimmed; empty notes with Available are stored as empty. | T5, T6, T8, T9; codes reused from K3 and F5 where the rule is the same. | 2026-11-26 | 6.3 |
| V5 | **Outcomes** (T3, T6, T7): the outcome becomes the asset's status. **Available**: can be assigned again. **Damaged**: cannot be assigned (J3 `asset_damaged`); a new request can be reported (O1). **Retired**: the asset's `retired_at`, `retired_by_user_id` and `retire_reason` (= the notes) are filled as Retire… does (F2); it becomes read-only (A3 / F8). Retire… itself still refuses Under Maintenance (`asset_not_retirable`). | T3, T6, T7; MNT-07, BR-05. | 2026-11-26 | 6.3 |
| V6 | **One transaction, two people at once:** lock the asset row, then the request row (as U5), re-read, check, then save the inspection, the asset's status (and retirement record) and the audit row(s) together; a failure saves nothing (tested by forcing the audit write to fail, for Available and Retired). Two inspections at the same moment: one wins, the other gets `request_not_awaiting_inspection` (tested; one audit row). | PRD 10; U5. | 2026-11-26 | 6.3 |
| V7 | **Audit and history (BR-13, MNT-06):** new action `maintenance.inspected` (added to the agreed list) on the asset: `before` request id and number, request status, asset status Under Maintenance; `after` the same ids, request status, new asset status, outcome, inspection date and condition notes. For Retired also the existing `asset.retired` row (`before` `{status: under_maintenance}`, `after` `{status: retired, reason, request id and number}`), so retirements look the same however they happened. The request page's History shows the `maintenance.inspected` row; the asset's History shows both. | BR-13, E2, S13, F6. | 2026-11-26 | 6.3 |
| V8 | **Screens:** an **Inspect…** form (request page and asset page, T11): inspection date (today, limited to between the earliest date and today), outcome (Available / Damaged / Retired) and condition notes with a 0 / 1,000 counter (0 / 500 and the label "reason for retiring" for Retired), "required for this outcome" unless Available. Confirm box "Inspect AST-… after MNT-… — result: Available?" with what happens ("It can be assigned again." / "It cannot be assigned. A new problem can be reported for it." / "This retires the asset permanently. It cannot be undone, and the asset becomes read-only."), the date, the notes and "An inspection is final and cannot be changed."; server refusals return to the form under their field (on top otherwise). **Request page:** an "Awaiting inspection" chip and Inspect… while awaiting; then an **Inspection** section (outcome, date, who and when, notes) and the request is read-only. **Asset page:** a note "Awaiting inspection after MNT-… (link). AST-… stays Under Maintenance until it is inspected." with Inspect…; Assign… greyed out "Awaiting inspection (MNT-…)."; Report a problem… greyed out "MNT-… is awaiting inspection. Inspect the asset first."; the requests table shows "Awaiting inspection" / "Inspected: …" under the status. **Maintenance list:** an "Awaiting inspection" status filter and the same note under each status. History: "Inspected · MNT-000001 · Under Maintenance → Available · inspected 26 Nov 2026 · Works fine". After saving: "AST-… inspected. Status: Available." | T11; K8 pattern; the plan approved by the owner. | 2026-11-26 | 6.3 |
| V9 | **Earlier tests adjusted to the new rule (T4):** two Slice 6.2 tests reported a new request right after a request was cancelled during repair; they now inspect it first (and one also checks the new refusal). The Slice 6.1 test-only shortcut that marks a request Completed now also records an inspection (outcome Available), so "a completed request does not block a new one" still means a finished, inspected request. No application behaviour from 6.1 / 6.2 changed otherwise. | T4. | 2026-11-26 | 6.3 (6.1, 6.2) |


---

## 37. Phase 6 questions answered by the owner (for Slice 6.4)

Twelve points raised with the Slice 6.4 plan and answered by the owner on 2026-11-26 (the recommended
options for all twelve, accepted as written). Already fixed and unchanged: MNT-08 (employees view the
status of their own submitted requests), PRD 4.1 / 4.2 (employees see only their own records), N8 / N15 /
L5 (My Assets, built in 5.3), N11 / L7 (the Employee home moves to My Dashboard in 6.4), N12 (no condition
notes or staff e-mails for Employees), N13 (the My pages are for the Employee role only), O3 / O6 / O7 / M3
(reporting only on assets held now; requests already made stay theirs to follow), O8 / Q10 (priority set by
staff), O9 (the reporter is the logged-in user), S11 (an Employee cannot cancel their own report), B18.

| # | Question | Owner's answer | Date | Affects slice(s) | Status |
|---|---|---|---|---|---|
| R1 | Do requests staff created on the Employee's asset appear in My Requests? | **No.** My Requests = the requests the login **reported** (MNT-08 "own submitted"; O9). | 2026-11-26 | 6.4 | Decided |
| R2 | Which request fields may an Employee see? | **Shown:** request number, asset (ID, name, serial), problem, status, reported date, work started date, completion date, cancelled date and the cancel reason. **Hidden:** priority (O8), service provider, repair notes, cost, staff e-mails (N12) and every inspection detail. | 2026-11-26 | 6.4 | Decided |
| R3 | How does the status read? | **The request status as stored** (Reported, In Progress, Completed, Cancelled). No "awaiting inspection" for Employees: it is an IT step after their request is done. | 2026-11-26 | 6.4 | Decided |
| R4 | Can an Employee cancel their own request? | **No** (S11 still applies). | 2026-11-26 | 6.4 | Decided |
| R5 | Can an Employee add comments? | **No.** Not in the PRD; a possible later feature. | 2026-11-26 | 6.4 | Decided |
| R6 | One page per request, or a list only? | **A list only**, with the progress in each row. | 2026-11-26 | 6.4 | Decided |
| R7 | Paging, search, filters on My Requests? | **Not paged**, newest first, no search and no filter (one person's requests stay few, as L5). | 2026-11-26 | 6.4 | Decided |
| R8 | Report a problem from My Requests? | **Yes:** a button that opens a picker of the assets held now (those with an open request shown but greyed out), then the existing report form. Greyed out with "You hold no assets." when nothing is held. | 2026-11-26 | 6.4 | Decided |
| R9 | What My Dashboard shows | **Three counts** (assets I hold, overdue returns, my open requests), the **overdue returns** list, the **open requests** list, and links to My Assets and My Requests. Nothing about other people; no charts. | 2026-11-26 | 6.4 | Decided |
| R10 | A login not linked to an employee record (L5) | The dashboard's asset part shows "Your login is not linked to an employee record." (My Assets already shows it); **My Requests still works**, since it goes by reporter. | 2026-11-26 | 6.4 | Decided |
| R11 | Home page | **Employees land on My Dashboard** (N11). A saved address the Employee may open still wins, as today. | 2026-11-26 | 6.4 | Decided |
| R12 | TEST logins for the browser check | **The owner signs in on the TEST app** for the Employee and staff checks while Claude checks the pages and the server log; no new logins are added to TEST. | 2026-11-26 | 6.4 | Decided |

---

## 38. Decisions in Slice 6.4 (✅ Slice 6.4 signed off by the owner, 2026-11-26; W1–W6 approved)

W1–W6 apply MNT-08, PRD 4.1 / 4.2 and the owner's answers R1–R12 (section 37). No new business rule beyond
those answers; no migration. **All of W1–W6 were approved with the Slice 6.4 sign-off (2026-11-26)**, after
the full backend run passed 1,087 tests, 300 frontend tests passed and the production build succeeded. The
browser check on the TEST database passed as an Employee (My Dashboard as home, reporting from My Requests,
following MNT-000004 to Completed after the asset was returned, no staff-only field in the response or on
the page, staff endpoints 403) and as an IT Manager (the My pages "Not allowed", the endpoint 403). For that
check the owner approved two TEST-only test logins (`itmanager.test64`, `employee.test64`, employee EMP-064),
made with the project's `create_user` development script instead of R12's owner sign-in.

| # | Decision | Why | Date | Slice |
|---|---|---|---|---|
| W1 | **No migration, read-only for the server:** My Requests is read from `maintenance_requests` by `reported_by_user_id`; My Dashboard is built from the two `/me` endpoints (no dashboard endpoint). Reading writes nothing (tested: the audit log is unchanged). | R1, R9; L1 pattern. | 2026-11-26 | 6.4 |
| W2 | **Endpoint:** `GET /api/v1/me/maintenance-requests`, **Employee role only** (Admin and IT Manager 403 `forbidden`, no login 401). The requests the login reported, newest first, not paged, also after the asset was returned (O6); a login not linked to an employee still gets its own requests. | R1, R6, R7, R10; N13, L6. | 2026-11-26 | 6.4 |
| W3 | **Employee-safe shape** (`MyRequestRow`): `request_number`, `asset` (`asset_code`, `name`, `serial_number` only), `issue_description`, `status`, `reported_date`, `started_date`, `completion_date`, `cancelled_date` (the cancel day in the company timezone) and `cancel_reason`. Hidden fields are **never sent** (tested: the response keys are exactly this set; priority, provider, notes, cost, inspection and e-mails do not appear). | R2, R3; PRD 4.1, N12, O8. | 2026-11-26 | 6.4 |
| W4 | **Privacy tests through the API:** an Employee sees only their own reports (not another Employee's, not staff-created ones on their asset); every staff maintenance endpoint (list, detail, start, complete, cancel, inspect, edit, the asset's requests, staff report) answers 403 to an Employee. | PRD 4.1; done-check. | 2026-11-26 | 6.4 |
| W5 | **Screens:** **My Requests** `/my/requests`: Request, Asset, Problem, Status, Reported on, Progress ("Waiting for the IT team" / "Work started 21 Nov 2026 · Completed 22 Nov 2026" / "Cancelled 21 Nov 2026 — Reason: …"); "No requests yet"; **Report a problem…** with the asset picker and the 6.1 form ("Problem reported: MNT-… The IT team will review it."). **My Dashboard** `/my/dashboard`: "Welcome, Asha Kumar.", counts Assets I hold / Overdue returns / My open requests, the overdue list ("AST-… — expected back … · 3 days overdue"), the open requests (number, asset, problem, status, reported date) and links to My Assets and My Requests. Both are read-only apart from reporting. | R6–R10; the plan approved by the owner. | 2026-11-26 | 6.4 |
| W6 | **Home page (N11):** `homePathFor('Employee')` is now `/my/dashboard`; the My pages stay Employee-only (staff are sent to "not allowed"). The Slice 5.3 test that checked the old home was updated. | R11; N11, L7, N13. | 2026-11-26 | 6.4 (5.3) |

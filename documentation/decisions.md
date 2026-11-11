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
2. **BR-12 (deactivate, don't delete):** Listed for employees (2.2) and vendors (2.3), but not for asset categories (2.1) or bulk stock items (2.4). Both of those are referenced by other records.
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

**Nothing OPEN blocks Slice 1.2.**

---

## 6. Slice 1.1 sign-off

- [x] Every PRD requirement ID is mapped to a slice
- [x] Questions 1–6 and 11 answered (needed for Phases 1–2)
- [x] Helper tools and server libraries approved
- [x] Phase 1 order fixes confirmed
- [x] No OPEN item blocks Slice 1.2
- [x] Owner says **"approved"**. Date: 2026-11-10

**Slice 1.1 is complete. Next: Slice 1.2 (Project setup).**

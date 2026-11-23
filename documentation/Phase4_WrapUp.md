# Phase 4 (Asset and inventory operations) — wrap-up

- **Status:** ✅ **Phase 4 signed off by the owner on 2026-11-23.** Slices 4.1–4.5 and decisions
  E1–E10, F1–F8, G1–G6, H1–H8 and I1–I8 are signed off (Slice 4.5 with this wrap-up, decisions.md
  section 25).
- **Date:** 2026-11-23
- **Phase goal (build plan):** "Users can view and manage assets and quantities." Met: every asset
  can be found by asset ID, serial number or name and opened on its own page with its full
  history; allowed details can be edited and assets retired with a reason; every stock item shows
  its balance, low-stock flag and movement history; stock is issued and adjusted with a reason and
  never goes below 0; equipment the company already owns is entered by hand (assets) or as opening
  stock (by-quantity items), all with audit rows.
- **Automated checks (Slice 4.5 code, 2026-11-23):** 815 backend tests pass (Phases 1–4); 195
  frontend tests pass in 17 files (`npm test`); the frontend production build has no errors.
  Migrations 0012 and 0013 (Phase 4) upgrade and downgrade cleanly (checked on the TEST database
  only); Slice 4.5 adds no migration and `alembic check` finds no difference on TEST.

---

## 1. PRD requirements for Phase 4: what was built

| PRD ID | Requirement (short) | Built in | Where / how | Status |
|---|---|---|---|---|
| AST-01 | Individual asset record with a unique asset ID | 3.2, **4.5** | Receiving (3.2) and now **Add existing asset** (`POST /assets`): the same system sequence AST-000001… (Q3, I1). | ✅ |
| AST-02 | Asset details: category, brand, model, serial, status, location, warranty, purchase | 2.1, 4.1 | Asset page `/assets/AST-000001`: Details, Purchase (or "Entered by hand") and History (E-decisions, I8). | ✅ |
| AST-03 | Search and filter assets | 4.1 | Assets page: search by asset ID, serial or name (any case); Category, Status, Location filters; server-side paging and sorting (E2–E6). The employee filter comes with assignments (A1 → Slice 5.1, E1). | ✅ (employee filter in 5.1) |
| AST-04 | Edit asset details | 4.2, 4.5 | **Edit**: name, brand, model, serial (still unique), location, warranty (A2, F1–F3); on assets entered by hand also category, purchase date and cost (A7a, I4). Status never changes by editing. | ✅ |
| AST-05 | Asset history | 4.1 | History section: every audit row about the asset, newest first (created, edited, retired; later assigned / returned / maintenance). | ✅ |
| AST-06 | No duplicate serial numbers | 3.2, 4.2, 4.5 | Unique ignoring case on receive, edit and manual entry; the database index catches two saves at the same moment (B62, I2). | ✅ |
| AST-07 | Retire an asset (status through actions only) | 4.2 | **Retire…**: only from Available or Damaged, required reason up to 500, cannot be undone, who / when / why stored (A3, F4–F6). | ✅ |
| INV-01 | Stock items with opening quantities | 2.4, **4.5** | Stock items (2.4) and **Enter opening stock…** once per item while it has no movements (A6, I5). | ✅ |
| INV-02 | Quantity on hand and reorder threshold | 2.4, 4.3 | Inventory list and stock item page `/inventory/:id` (G3). | ✅ |
| INV-04 | Issue stock | 4.4 | **Issue…**: quantity, required reason, optional active employee, date (A4, H1). | ✅ |
| INV-05 | Dated movement history: type, quantity, reference, user | 3.3, 4.3–4.5 | Movement history on the stock item page: date, type (Receipt / Issue / Adjustment in / out / Opening stock), change, balance after, reference (purchase or "Issued to …"), reason / note, saved at and by whom (G2, G4, H7, I8). | ✅ |
| INV-06 | Low-stock flag | 4.3 | Active and at or below the reorder threshold; badge and **Stock level** filter (G1, G5). | ✅ |
| INV-07 | Stock never below zero | 3.3, 4.4 | `record_movement()` refuses it (`insufficient_stock`); the screen checks first; two issues at once cannot both pass (C7, H5). | ✅ |
| BR-09 | Every movement records item, quantity, type, date/time, reason, user | 3.3, 4.4, 4.5 | All columns; reason required for issue / adjust (C3, H4), optional note for opening stock (I5). | ✅ |
| BR-10 | Bulk stock cannot go negative | 4.4 | As INV-07. | ✅ |
| BR-13 | Important actions in the audit log | 4.2, 4.4, 4.5 | `asset.updated`, `asset.retired`, `stock.issued`, `stock.adjusted`, `asset.created` (manual), `stock.opening`, each in the same transaction as the change (F7, H6, I6). | ✅ |
| Q4 | Entering equipment already owned | 4.5 | Manual asset entry + one-time opening stock (A6, A7). | ✅ |
| Workflow 7.5 | Issue / adjust with a confirm box, no approval step | 4.4 | Form, then confirm box with the balance now and after (Q7, H8). | ✅ |

Also delivered in Phase 4 (from decisions, not new PRD IDs):
- **Clickable rows and detail pages** for assets and stock items (D7, E7, G3).
- **Row locks** so two people changing the same asset or stock item at the same moment cannot
  both succeed (F8, H5, I5).
- **Optional employee on issues** (migration 0013, A4), shown as "Issued to Asha Kumar (EMP-001)".

Hooks left ready for later phases:

| Hook | Used from | What it does |
|---|---|---|
| `AssetStatus` Assigned / Under Maintenance, `RETIRABLE_STATUSES` | **5.1, 5.2, 6.2** | Assigning and maintenance set these statuses; Assigned and Under Maintenance assets cannot be retired (A3). |
| Asset history (`GET /assets/{ref}/history`) | **5.x, 6.x** | Assignment, return and maintenance audit rows appear on the asset page automatically. |
| `EmployeePicker` (`onlyWithoutLogin`) | **5.1** | Choosing an active employee to assign to. |
| `DataTable` filters / `filtersActive` | **5.1, 5.3** | Employee filter on the asset register (A1); overdue list. |
| `stock_movements.issued_to_employee_id` | reports (7.x) | Consumables issued per employee. |

---

## 2. Manual test steps for the whole phase

Start the backend and frontend (README sections 4–5) and run `.venv\Scripts\alembic upgrade head`
first (migrations 0012–0013; Slice 4.5 adds none). Log in as **Admin** unless a step says
otherwise. You need, from Phases 2–3: a one-by-one category "Laptops", a by-quantity category
"Peripherals", a stock item "USB mouse" with some stock received on a purchase, a few received
laptops (AST-000001…) and an active employee "Asha Kumar (EMP-001)".

### Asset register (4.1)
1. **Assets:** the list shows Asset ID, Name, Category, Serial number, Model, Location and Status,
   newest asset ID first. Search a whole asset ID, part of a serial in another case, and part of a
   name → each finds the asset (build-plan done-check).
2. Filter by **Category**, **Status** and **Location** together; an empty result says "No matches";
   **Clear filters** resets them. Click a row (or Tab to it and press Enter) → the asset page.
3. Asset page: Details, **Purchase** (purchase and vendor links, invoice no., purchase date, cost)
   and **History** ("Created — Received on purchase PUR-…"). `/assets/AST-999999` → "Asset not found".

### Edit and retire (4.2)
4. **Edit** a received laptop: change the location and the serial → saved, and History shows
   "Location: A → B; Serial number: …". Category, purchase, purchase date and cost are shown
   read-only. A serial used by another asset (any case) or a warranty before the purchase date is
   refused under the field.
5. **Retire…** an Available laptop: the box says it cannot be undone; the reason is required (0 /
   500). After retiring: status Retired, "Retired by" and the reason shown, no Edit or Retire, and
   History shows the reason (build-plan done-check).

### Stock balances (4.3)
6. **Inventory:** an item at or below its reorder threshold shows an orange **Low stock** badge;
   the **Stock level** filter shows only those. Click an item name → the stock item page with
   quantity on hand, threshold, stock level and **Movement history** (Receipt with a link to its
   purchase) (build-plan done-check).

### Issue and adjust (4.4)
7. On **USB mouse**: **Issue…** more than is in stock → "Only N in stock." under Quantity. Issue
   3 with a reason, optionally to Asha Kumar → confirm box with the balance now and after → saved;
   the history shows "Issued to Asha Kumar (EMP-001)", the reason and who saved it (build-plan
   done-check).
8. **Adjust…** → Add 2 "Found in the store room", then Remove 1 "Broken" → balances follow. A
   future date or an empty reason is refused. An inactive item has Issue… and Adjust… greyed out.

### Existing equipment (4.5)
9. **Assets → Add existing asset:** the Category list shows only **active one-by-one** categories.
   Save with nothing filled → Category, Name, Serial number and Model are required.
10. Category Laptops, name "Dell Latitude 7490", serial `OLD-5001`, model "Latitude 7490",
    location "Pune office", purchase date 2023-04-01, warranty 2026-04-01, cost 64999.50 →
    **Add asset** → "AST-0000NN added." and the new asset's page opens: the next asset ID in the
    same sequence as received laptops, status **Available**, an **Entered by hand** chip, and the
    Purchase section says "Entered by hand (existing equipment, no purchase or vendor)" with the
    purchase date and cost (build-plan done-check, laptop).
11. Add another existing asset with serial `old-5001` → "already used" under Serial number;
    a future purchase date, a warranty before the purchase date, or cost `-1` / `1.234` → refused
    under the field. Nothing is saved.
12. On that hand-entered asset, **Edit**: Category, Purchase date and Cost are editable; change the
    cost → History shows "Cost: ₹64,999.50 → …". On a **received** laptop the Edit box still shows
    them read-only.
13. **Inventory → Add item** "HDMI cable" (Peripherals, pieces, threshold 5) and open it: **Enter
    opening stock…** is shown. Enter 40, note "Counted in the store room" → confirm box "Enter
    opening stock of 40 pieces for HDMI cable?" with "On hand: 0 → 40 pieces." → saved; on hand is
    40 and the history shows **Opening stock** with the note (build-plan done-check, cable).
14. The button is gone after that; on **USB mouse** (which has receipts) it never appears, and
    not on an inactive item. (Through the API, a second opening entry gets
    `opening_stock_not_allowed`.)

### Roles and audit (all slices)
15. Log in as an **IT Manager**: everything above works.
16. Log in as an **Employee**: Assets and Inventory are not in the menu; opening `/assets`,
    `/assets/AST-000001` or `/inventory/1` directly shows **Not allowed** (the server answers 403).
17. Audit trail (until the Audit Log screen arrives in 8.1):

    ```powershell
    & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -p 5433 -U itam_app -d itam_dev -c "SELECT created_at, action, entity_type, entity_id, actor_user_id FROM audit_logs WHERE action LIKE 'asset.%' OR action LIKE 'stock.%' ORDER BY id DESC LIMIT 30;"
    ```

    Expect `asset.created` (also for the hand-entered asset), `asset.updated`, `asset.retired`,
    `stock.issued`, `stock.adjusted` and `stock.opening` rows with the acting user's id.

---

## 3. What Phase 5 (Assignment and return) needs from the owner first

Phase 5 slices (build plan): **5.1** assign an Available asset to an active employee (assignment
date, assigned-by, optional expected return date; confirm box; one transaction with audit),
**5.2** return with inspection on the same form (Q5; the asset becomes Available, Under
Maintenance or Damaged), **5.3** history and overdue returns (employee page with current and past
assets; overdue list). Questions the PRD and decisions.md don't settle; a suggested answer is in
italics. The team will not decide these alone.

| # | Question | Blocks |
|---|---|---|
| A1 | **Employee filter on the asset register** (postponed from 4.1, E1): add it in 5.1 as a filter "Assigned to" (current holder) plus an **Assigned to** column? *(Proposed: yes, both in 5.1; the filter lists active and inactive employees, since an inactive employee may still hold an asset.)* | 5.1 |
| N1 | **Assignment date:** today by default; may an earlier date be entered (recording handovers that already happened)? *(Proposed: today by default, earlier allowed, future refused, company timezone, the same as A4-5a; not before the asset was created.)* | 5.1 |
| N2 | **Expected return date:** optional (ASN-02). If given, must it be after the assignment date? *(Proposed: optional; on or after the assignment date; changeable later only by returning and assigning again, no separate edit in v1.)* | 5.1, 5.3 |
| N3 | **Who can be assigned to:** any active employee, or only employees with a login? *(Proposed: any active employee; a login is not needed (Q6). Inactive employees are refused (EMP-05, BR-05).)* | 5.1 |
| N4 | **Return form (Q5):** which fields are required? *(Proposed: return date (today by default, earlier allowed but not before the assignment date, never future) and the inspection outcome (Available / Under Maintenance / Damaged) required; condition notes optional, up to 1,000 characters, but required when the outcome is Damaged or Under Maintenance.)* | 5.2 |
| N5 | **Return as "Under Maintenance":** should it also open a maintenance request, which only arrives in Phase 6? *(Proposed: no; 5.2 only sets the status and records the notes. Phase 6 adds requests; the IT Manager opens one then.)* | 5.2, 6.1 |
| N6 | **Deactivating an employee who still holds assets:** allowed, warned, or blocked? *(Proposed: blocked with a clear message listing the assets (`employee_has_assets`) until they are returned.)* | 5.1 |
| N7 | **Overdue:** an assignment is overdue when its expected return date is before today (company timezone) and it is not returned. Who sees the overdue list? *(Proposed: that definition; Admin and IT Manager only, as a page / filter in 5.3; no e-mail reminders in v1, as with warranties.)* | 5.3 |
| N8 | **Employee role:** does an Employee who logs in see their own current assets (and past ones) in Phase 5, or does "My Assets" wait for the dashboard (7.1)? *(Proposed: a read-only "My assets" page in 5.3 showing their current assets and past assignments, using the login–employee link (Q6).)* | 5.3 |
| N9 | **Who can assign and return:** *(Proposed: Admin and IT Manager only, the same as every other asset action.)* | 5.1, 5.2 |

Still open from earlier:
- **R2** (temporary passwords, before Slice 8.3) and **Q12** (hosting and domain, before Slice 8.5)
  don't block Phase 5.
- ~~Sign-off of Slice 4.5 decisions I1–I8 and of Phase 4~~: **✅ signed off by the owner on 2026-11-23.**

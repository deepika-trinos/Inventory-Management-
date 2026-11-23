# Phase 3 (Purchase and receiving) — wrap-up

- **Status:** ✅ **Phase 3 signed off by the owner on 2026-11-20.** Slices 3.1–3.4 and decisions
  B42–B66, C1–C12 and D1–D10 are signed off (D8 tightened at approval: `reset_password` runs
  only with `APP_ENV=development` explicitly set; D10 fixed the Purchases "No matches" message
  found during the manual test run). All 18 manual test steps in section 2 passed on
  2026-11-20 on the TEST database.
- **Date:** 2026-11-16
- **Phase goal (build plan):** "Purchases reliably create asset or stock records." Met: a draft
  purchase changes nothing; receiving it creates one asset per one-by-one unit (with a new asset
  ID) and raises stock for by-quantity lines with a matching stock movement, all in one
  transaction with audit rows; every purchase can be found again from the purchase list and its
  vendor's page.
- **Automated checks (re-run 2026-11-20 on the Slice 3.4 code, after the D8 change):**
  556 backend tests pass (Phases 1–3); 109 frontend tests pass in 9 files (after the D10 fix)
  (`npm test`); migrations 0008–0011 upgrade and downgrade cleanly (checked on the test database
  only); the frontend production build has no errors.

---

## 1. PRD requirements for Phase 3: what was built

| PRD ID | Requirement (short) | Built in | Where / how | Status |
|---|---|---|---|---|
| PUR-01 | Create a purchase record linked to a vendor | 3.1 | **New purchase** form; `POST /purchases`. Only active vendors (B33). | ✅ |
| PUR-02 | Reference / invoice no., purchase date, received date, item, quantity, unit cost, notes | 3.1, 3.2 | All fields. Reference unique per vendor ignoring case (P3, B43); purchase date not in the future (B48); received date set on receipt (B58). | ✅ |
| PUR-03 | Several line items per purchase | 3.1 | Lines list; one-by-one and by-quantity lines may be mixed (P1). | ✅ |
| PUR-04 | Draft, received or cancelled | 3.1–3.3 | Status with badges; received and cancelled are final (P6). | ✅ |
| PUR-05 | Inventory changes only when items are confirmed received | 3.2, 3.3 | Only `POST /purchases/{id}/receive` (after a confirm box) creates assets or stock. | ✅ |
| PUR-06 | One asset per serialized unit received | 3.2 | Each unit row becomes an asset AST-000001… with status Available (B60). | ✅ |
| PUR-07 | Bulk items raise the stock quantity by the received quantity | 3.3 | One `receipt` movement per by-quantity line, balance updated in the same transaction (C9, C11). | ✅ |
| PUR-08 | Draft or cancelled purchases never increase stock | 3.1 | Nothing in create / edit / cancel touches stock or assets; tests prove balances and asset counts stay the same. | ✅ |
| PUR-09 | Purchase history with vendor / item details | 3.4 | Purchase list (search; status, vendor and purchase-date range filters) and detail page `/purchases/:id`: vendor and contacts, lines with ordered / received quantities, unit cost, totals, assets created, stock movements, created / received by and when (D1–D6). | ✅ |
| AST-01 | Individual asset record with a unique asset ID | 3.2 (and 4.5 for manual entry) | System IDs AST-000001… from a database sequence (Q3, B60). | ✅ for receiving |
| AST-06 | No duplicate serial numbers | 3.2 | Unique ignoring case across all assets (index + checks), per-row errors (B62). | ✅ |
| INV-03 | Stock increases from confirmed purchase receipts | 3.3 | Receipt movements (C9). | ✅ |
| INV-05 | Dated movement history: type, quantity, reference, user | 3.3 (data), 3.4 (shown per purchase) | Append-only `stock_movements` (C10) with business date and save time (C2), purchase line as reference (C3), balance after (C4), responsible user. Shown on the purchase detail; the full per-item history screen is Slice 4.3. | ✅ for receipts |
| VEN-04 | Purchase history of a vendor | 3.4 | Vendor page section, newest purchase date first, paged; inactive vendors included; a row opens the purchase (D2, D4, D6). | ✅ |
| BR-01 | Every serialized asset has a unique asset ID | 3.2 | Database sequence + unique column (B60). | ✅ |
| BR-06 | Draft or cancelled purchases never increase inventory | 3.1 | As PUR-08. | ✅ |
| BR-07 | Only confirmed received quantities update inventory | 3.2, 3.3 | The received quantity per line (0 to ordered, P4) is what becomes assets / stock (B58, C1). | ✅ |
| BR-08 | Serialized → assets; bulk → quantity-based stock | 3.1–3.3 | Line types (P1, B47); categories lock their tracking type once used (B46, B63). | ✅ |
| BR-09 | Movement records item, quantity, type, date/time, reference/reason, user | 3.3 | All columns present; `reason` ready for adjustments (C3, Slice 4.4). | ✅ |

Also delivered in Phase 3 (from decisions, not new PRD IDs):
- **BR-13:** audit rows `purchase.created`, `purchase.updated`, `purchase.cancelled`,
  `purchase.received` and one `asset.created` per asset, each in the same transaction as the change
  (B50, B64, C8). Stock movements are their own append-only history (C8, C10).
- **One transaction per receipt (PRD 10):** status, quantities, assets, movements, balances and
  audit are saved together or not at all; tests force failures to prove it.
- **INV-07 / BR-10 groundwork:** `record_movement()` refuses negative stock (`insufficient_stock`,
  C7), ready for Slice 4.4.
- **Frontend tests (T1):** Vitest + React Testing Library at pinned versions (B54, B66).

Hooks left ready for later slices:

| Hook | Used from | What it does |
|---|---|---|
| `inventory.record_movement()` / `lock_stock_items()` | **4.4, 4.5** | The one way to change stock: movement + balance in the caller's transaction, row locks in id order (C11) |
| `stock_movements.reason` | **4.4** | Optional now; to become required for adjustments (C3) |
| `assets` table, `GET /assets/{id or asset ID}`, `AssetDetailsDialog` | **4.1, 4.2, 4.5** | Asset register, edit / retire, manual entry (B60, B65) |
| `DataTable` `onRowClick` | **4.1, 4.3** | Clickable rows for asset and stock history lists (D7) |
| `purchases.received_by_user_id` / `received_at` | reports (7.x) | Who received what, and when (D1) |

---

## 2. Manual test steps for the whole phase

Start the backend and frontend (README sections 4–5) and run `.venv\Scripts\alembic upgrade head`
first (migrations 0008–0011). Log in as **Admin** unless a step says otherwise. You need an
active vendor "Acme IT Supplies", a one-by-one category "Laptops", a by-quantity category
"Peripherals" and a stock item "USB mouse" (Phase 2 steps 1, 10 and 14).

### Draft purchases (3.1)
1. **Purchases → New purchase:** only active vendors are offered. Vendor Acme, reference
   `INV-2026-0042`, today's date. Line 1 **One-by-one**: Laptops, "Laptops: Dell Latitude 5440",
   3 × 85000. **Add line**, line 2 **By quantity**: USB mouse, 10 × 450. Line totals ₹2,55,000.00
   and ₹4,500.00, total ₹2,59,500.00. **Save draft** → PUR-000001, **Draft**.
2. **Inventory:** the mouse's "On hand" is unchanged.
3. A second purchase with reference `inv-2026-0042` for Acme → refused; for another vendor → allowed.
   A future date, quantity 0 or cost -1 → refused; cost 0 → allowed.
4. Edit the draft (pencil icon), change a quantity → totals change. Create another draft and
   **Cancel** it (confirm box) → **Cancelled**; stock unchanged; it can no longer be edited.
5. **Categories → edit Laptops → By quantity** → refused (`tracking_type_locked`).

### Receive one-by-one items (3.2)
6. Make a draft with 3 laptops only. Click the **Receive** (inbox) icon: received date today, 3 unit
   rows. Fill serial and model for unit 1, use **Copy unit 1 to all units**, then give units 2 and 3
   their own serials. Typing a serial twice, or a warranty date before the purchase date, is marked
   on that row.
7. **Receive** → confirm box → success message with AST-000001 to AST-000003. The purchase is
   **Received**; click an asset ID → its details (category, serial, model, purchase, cost).
8. Receive another purchase using serial `sn-1` (an existing serial in another case) → refused on
   that row; nothing is saved.

### Receive by-quantity and mixed purchases (3.3)
9. Receive PUR-000001 (3 laptops + 10 mice). The mouse line shows "Ordered: 10 pieces" and "In
   stock now: N pieces · after receiving: N+10 pieces". Receive → message lists the new assets and
   "stock added: USB mouse +10 pieces". **Inventory:** the mouse's on-hand rose by 10.
10. Receive a mouse line as **0** with another line above 0 → allowed, no stock added for it.
    Deactivating a stock item (at 0 stock) and receiving a purchase that adds to it → refused on
    that line.

### Purchase history (3.4)
11. **Purchases:** the list shows Purchase no., Vendor, Invoice / ref., Purchase date, **Received**,
    Lines, Total and Status. Search "acme", "inv-2026" and "PUR-000001". Filter by Status and
    Vendor. Set **Purchase date from / to** around one purchase's date → only purchases dated
    in that range (both days included). Set "from" after "to" → the "to" field turns red and the
    table explains the problem. **Clear filters** resets them.
12. Click **PUR-000001** (or **View**) → detail page: vendor (link) with contact details, invoice
    no., purchase and received dates, **Created by** and **Received by** with times, the lines
    with ordered and received quantities, unit cost, line totals and total, **Assets created**
    (asset IDs and serials; click one) and **Stock movements** (Receipt, +10 pieces, balance
    after, date, who). No Edit / Receive / Cancel buttons: "Received purchases are final".
13. Open a **cancelled** purchase → read-only, "A cancelled purchase never changes stock or creates
    assets" in both sections. Open a **draft** → Edit, Receive… and Cancel purchase are there.
14. Open `/purchases/99999` → "Purchase not found" with a link back to all purchases.
15. Click the vendor link → **Vendors → Acme**: the **Purchase history** lists its purchases,
    newest purchase date first, with the same total for PUR-000001 as the Purchases list
    (build-plan done-check). Click a row → its detail page. Deactivate Acme → its history is still
    shown.

### Roles and audit (all slices)
16. Log in as an **IT Manager**: everything above works.
17. Log in as an **Employee**: Purchases and Vendors are not in the menu; opening `/purchases`,
    `/purchases/1` or `/vendors/1` directly shows **Not allowed** (the server also answers 403).
18. Audit trail (until the Audit Log screen arrives in 8.1):

    ```powershell
    & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -p 5433 -U itam_app -d itam_dev -c "SELECT created_at, action, entity_type, entity_id, actor_user_id FROM audit_logs WHERE action LIKE 'purchase.%' OR action = 'asset.created' ORDER BY id DESC LIMIT 30;"
    ```

    Expect `purchase.created`, `purchase.updated`, `purchase.cancelled`, `purchase.received` and
    `asset.created` rows with the acting user's id. Stock movements:
    `SELECT * FROM stock_movements ORDER BY id DESC;`

---

## 3. What Phase 4 (Asset and inventory operations) needs from the owner first

Questions the PRD and decisions.md don't settle. A suggested answer is in brackets; the team
will not decide these alone.

| # | Question | Blocks |
|---|---|---|
| A1 | **Asset register filters (4.1):** the plan lists an "employee" filter, but assignments only arrive in Phase 5. Build the filter now (always empty until 5.1) or add it in Slice 5.1? *(Proposed: add it in 5.1.)* | 4.1 |
| A2 | **Editable asset fields (4.2):** which can be changed after creation? Name, brand, model, location, warranty expiry, and the serial number (still unique)? Can category, purchase date or cost be changed on an asset that came from a purchase? *(Proposed: name, brand, model, serial, location, warranty editable; category, purchase link, purchase date and cost locked for received assets, editable for manually entered ones.)* | 4.2 |
| A3 | **Retiring (4.2):** from which statuses? Available, Damaged and Under Maintenance only (an Assigned asset must be returned first)? Is the reason free text (max length?) or a fixed list? *(Proposed: not while Assigned; free text, required, up to 500 characters.)* | 4.2 |
| A4 | **Stock issue (4.4):** must an issue name who received the items (an employee, a department, or free text), or only a reason? *(Proposed: optional employee plus required reason.)* | 4.4 |
| A5 | **Stock adjustment (4.4):** entered as "+/- N" (a change) or as "counted N" (the system works out the change)? *(Proposed: "+/- N" with a required reason; counting can come later.)* | 4.4 |
| A6 | **Opening stock (4.5):** allowed only once per item and only while it has no movements at all? Who may enter it? *(Proposed: once per item, only with no movements yet; Admin and IT Manager.)* | 4.5 |
| A7 | **Manual asset entry (4.5):** same required fields as receiving (serial and model; P5)? Purchase date, cost and vendor optional? Always created as Available? *(Proposed: yes; optional purchase date and cost, no vendor; always Available.)* | 4.5 |

**Answered since:** A1 (decisions.md E1, 2026-11-20); A2 and A3 (decisions.md section 19, 2026-11-22); A4 and A5 (decisions.md section 22, 2026-11-23). A6–A7 are still open.

Still open from earlier:
- **R2** (temporary passwords) and **Q12** (hosting and domain) don't block Phase 4.
- ~~Sign-off of Slice 3.4 decisions~~: **D1–D9 approved 2026-11-20.**
- ~~Manual test run~~: **all 18 steps of section 2 passed on 2026-11-20**, run on the TEST database (`itam_test`) as Admin, IT Manager and Employee.
  One wording problem was found (step 11: an empty filtered Purchases list said "No purchases yet") and fixed at the owner's request (D10).
- ~~Sign-off of Phase 3~~: **✅ signed off by the owner on 2026-11-20.**

# Phase 2 (Master data) — wrap-up

- **Status:** all four slices built. 2.1, 2.2 and 2.3 are signed off; **2.4 awaits sign-off**,
  and with it Phase 2.
- **Date:** 2026-11-12
- **Phase goal (build plan):** "Core reference records are available." Met: categories,
  employees, vendors and bulk stock items can be created, found, edited and deactivated, never
  deleted, and every change is in the audit log.
- **Automated checks:** 351 backend tests pass (Phase 1 + 2); migrations 0004–0007 upgrade and
  downgrade cleanly; the frontend production build has no errors.

---

## 1. PRD requirements for Phase 2: what was built

| PRD ID | Requirement (short) | Built in | Where / how | Status |
|---|---|---|---|---|
| AST-02 | Store asset name, **category**, brand, model, … | 2.1 (category part) | Asset categories with name, description and tracking type (one-by-one / by quantity). The other asset fields arrive with assets in **3.2 / 4.1** (as the plan maps AST-02 to 2.1 + 4.1). | ✅ for Phase 2 |
| EMP-01 | Create, view and update employee records | 2.2 | Employees page + `/api/v1/employees` (create, get, edit, list) | ✅ |
| EMP-02 | Employee ID, name, department, designation, work email, contact details, employment status | 2.2 | All fields; contact details = phone (B22); status active/inactive | ✅ |
| EMP-03 | Search employees by ID, name or department | 2.2 | One search box matches all three (any case); department filter | ✅ |
| VEN-01 | Create, view and update vendor records | 2.3 | Vendors page, vendor detail page `/vendors/:id`, `/api/v1/vendors` | ✅ |
| VEN-02 | Vendor name, contact person, email, phone, address where available | 2.3 | Only the name is required (B31) | ✅ |
| VEN-03 | Search and filter vendor records | 2.3 | Search name / contact / email / phone; status filter | ✅ |
| VEN-05 | No deletion of a vendor referenced by purchases; deactivate instead | 2.3 | No delete at all (405); deactivate/activate; `ensure_vendor_active()` ready for 3.1 | ✅ (see question P8) |
| INV-01 | Inventory item records: name, category, unit of measure, reorder threshold | 2.4 | Stock items: bulk categories only, fixed unit list, threshold ≥ 0, read-only quantity | ✅ (opening stock part: 4.5) |
| BR-12 | Referenced records are deactivated, not deleted | 2.1–2.4 | No DELETE endpoint for categories, employees, vendors or stock items (all answer 405); activate/deactivate everywhere; tests prove it | ✅ |

Also delivered in Phase 2 (from decisions, not new PRD IDs):
- **Order fix b / R3:** every Employee-role login must be linked to an employee; older unlinked
  logins keep working and are flagged "Needs employee link". **B12 closed:** employee picker on
  the Users screens.
- **BR-13:** audit rows for every create, edit, activate and deactivate of the four record types,
  plus user-to-employee link changes and logins deactivated together with their employee.
- **PRD 9.2:** a stock item must sit in a "by quantity" category, so the same units can never be
  counted as both assets and stock. A category used by stock items can no longer switch its
  tracking type. Inventory model chosen: stored balance plus movement history (B39).

Hooks left ready for later slices (each marked in code comments):

| Hook | Used from | What it does |
|---|---|---|
| `categories.ensure_category_selectable()` | 2.4 (in use), 3.2 | Inactive categories can't be chosen for new records |
| `categories._category_in_use()` | 2.4 (stock items), **3.2 must add assets** | Locks a category's tracking type |
| `vendors.ensure_vendor_active()` | **3.1** | Purchases only from active vendors |
| `inventory.ensure_stock_item_usable()` | **3.1, 4.4, 4.5** | Inactive stock items can't be used |
| `inventory._has_stock_history()` | **3.3 must add movements** | Locks the unit of measure |
| Vendor page "Purchase history" placeholder | **3.4** | VEN-04 |
| Employee `status` | **5.1** | EMP-05: no new assignments to inactive employees |

---

## 2. Manual test steps for the whole phase

Start the backend and frontend (README sections 4–5). Log in as **Admin** unless a step says otherwise.

### Categories (2.1)
1. **Categories → Add category:** "Laptops", **One-by-one**. Then "Peripherals", **By quantity**. Both appear.
2. Add "LAPTOPS" → refused: *already exists*.
3. Edit Peripherals' description → saved.
4. Deactivate Laptops → confirm box → status **Inactive**; it is still listed. There is no Delete button.

### Employees (2.2)
5. **Employees → Add employee:** `EMP-001`, "Asha Kumar", department "Finance", work email `Asha@Example.com`, phone `+91 98765 43210` → email shown in lower case.
6. Add `emp-001` → refused (employee ID taken). Type "fin" in a new employee's Department → "Finance" is suggested.
7. Search "asha", "EMP-0" and "finance" → Asha is found each time. Try the Department and Status filters.
8. **Users → Create user** with role **Employee** and no employee → blocked. Pick "EMP-001 · Asha Kumar" → created, and the list shows "Asha Kumar (EMP-001)".
9. Log in as Asha in another browser (private window) → it works. Back as Admin, **Employees → deactivate Asha** → the confirm box warns that her login will be deactivated too → her next click signs her out.

### Vendors (2.3)
10. **Vendors → Add vendor:** save with no name → *Please enter the vendor's name*. Enter "Acme IT Supplies", email `sales@acme` → refused (invalid email); fix it to `Sales@Acme.Example.com` → saved in lower case.
11. Add "ACME it supplies" → refused (already exists).
12. Search by contact person, email and phone; use the Status filter.
13. Click the vendor name → detail page with details and a **Purchase history — Coming in Slice 3.4** box. **Deactivate** → confirm → **Inactive**. Open `/vendors/9999` → *Vendor not found*.

### Stock items (2.4)
14. **Inventory → Add stock item:** the Category list shows only **Peripherals** (Laptops is one-by-one and inactive). "USB mouse", unit **Pieces**, threshold **10** → listed with **On hand 0**.
15. Add "usb MOUSE" in Peripherals → refused (name taken). Threshold `-1` → refused.
16. Edit the mouse → *Quantity on hand* is greyed out (read-only).
17. **Categories → edit Peripherals → switch to One-by-one** → refused (*tracking type cannot be changed*, because the mouse uses it).
18. Deactivate the mouse → confirm → **Inactive**.

### Roles and audit (all slices)
19. Log in as an **IT Manager**: Categories, Employees, Vendors and Inventory all work. Users and Audit Log are not in the menu.
20. Log in as an **Employee**: none of these pages are in the menu; opening `/vendors` directly shows **Not allowed** (the server also answers 403).
21. Audit trail (until the Audit Log screen arrives in 8.1):

    ```powershell
    & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -p 5433 -U itam_app -d itam_dev -c "SELECT created_at, action, entity_type, entity_id, actor_user_id FROM audit_logs ORDER BY id DESC LIMIT 30;"
    ```

    Expect `category.*`, `employee.*`, `vendor.*`, `stock_item.*`, `user.employee_link_changed` and `user.deactivated` rows, each with the acting user's id.

---

## 3. What Phase 3 (Purchases) needs from the owner first

Questions the PRD and decisions.md don't settle (proposed answers in brackets):

| # | Question | Blocks |
|---|---|---|
| P1 | **What does a purchase line point to?** Bulk lines → a stock item. Serialized lines → a **category plus a free-text description** (e.g. "Laptops — Dell Latitude 5440")? *(Proposed: yes.)* | 3.1 |
| P2 | **Money:** one currency (INR) only? Unit cost with 2 decimal places? Is a cost of 0 allowed (free/replacement items)? *(Proposed: INR, 2 decimals, 0 allowed. No tax, which the PRD excludes.)* | 3.1 |
| P3 | **Invoice / reference number:** required? Unique per vendor? *(Proposed: required, unique per vendor, ignoring case.)* Can the purchase date be in the future? *(Proposed: no.)* | 3.1 |
| P4 | **Received quantity vs ordered (Q2 = no partial receipts):** must the received quantity equal the ordered quantity, or can it be lower (short delivery), closing the line? *(Proposed: lower allowed, never higher; the line is then closed.)* | 3.2, 3.3 |
| P5 | **Serialized receiving:** which unit details are required: serial number, brand, model, warranty expiry, location (Q1: typed)? *(Proposed: serial number and model required, the rest optional.)* Are serial numbers unique across all assets or per brand? *(Proposed: all assets, ignoring case — AST-06.)* | 3.2 |
| P6 | **Who may receive or cancel a purchase:** Admin and IT Manager both? Can a **received** purchase ever be cancelled or corrected? *(Proposed: both roles; received purchases are final, and errors are fixed by stock adjustment in 4.4 or retiring the asset.)* | 3.1–3.3 |
| P7 | **Stock movement types** to fix now for 3.3/4.4/4.5: `receipt`, `issue`, `adjustment_in`, `adjustment_out`, `opening`? *(Proposed: yes.)* | 3.3 |
| P8 | VEN-05 only forbids deleting vendors **with** purchases; we never delete vendors at all (BR-12). Keep that? *(Proposed: keep.)* | — |

Still open from earlier:
- **T1:** approve a frontend test tool (Vitest + React Testing Library). It is "recommended before Phase 3"; the purchase and receiving screens are the most complex so far.
- **R2** (temporary passwords) and **Q12** (hosting) don't block Phase 3.

Also: a **sign-off of Slice 2.4 / Phase 2**, including decisions **B35–B41**.

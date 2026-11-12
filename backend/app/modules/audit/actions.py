"""Every audit action name, in ONE place.

Format: "<thing>.<what_happened>" in lower case. Always use these constants,
never a typed string: audit.record() refuses unknown names, so a typo fails a
test instead of silently writing a wrong action.

The slice that will start using each one is noted on the right.
"""


class AuditAction:
    # Users and roles
    USER_CREATED = "user.created"  # Slice 1.6
    USER_UPDATED = "user.updated"  # Slice 1.6
    USER_ROLE_CHANGED = "user.role_changed"  # Slice 1.4 (service), 1.6 (endpoint)
    USER_ACTIVATED = "user.activated"  # Slice 1.6
    USER_DEACTIVATED = "user.deactivated"  # Slice 1.6 (also when the linked employee is deactivated, Slice 2.2)
    USER_EMPLOYEE_LINK_CHANGED = "user.employee_link_changed"  # Slice 2.2

    # Employees (master data)
    EMPLOYEE_CREATED = "employee.created"  # Slice 2.2
    EMPLOYEE_UPDATED = "employee.updated"  # Slice 2.2
    EMPLOYEE_ACTIVATED = "employee.activated"  # Slice 2.2
    EMPLOYEE_DEACTIVATED = "employee.deactivated"  # Slice 2.2

    # Asset categories (master data)
    CATEGORY_CREATED = "category.created"  # Slice 2.1
    CATEGORY_UPDATED = "category.updated"  # Slice 2.1
    CATEGORY_ACTIVATED = "category.activated"  # Slice 2.1
    CATEGORY_DEACTIVATED = "category.deactivated"  # Slice 2.1

    # Vendors (master data)
    VENDOR_CREATED = "vendor.created"  # Slice 2.3
    VENDOR_UPDATED = "vendor.updated"  # Slice 2.3
    VENDOR_ACTIVATED = "vendor.activated"  # Slice 2.3
    VENDOR_DEACTIVATED = "vendor.deactivated"  # Slice 2.3

    # Purchases
    PURCHASE_RECEIVED = "purchase.received"  # Slices 3.2-3.3
    PURCHASE_CANCELLED = "purchase.cancelled"  # Slice 3.1

    # Assets
    ASSET_CREATED = "asset.created"  # Slices 3.2, 4.5
    ASSET_RETIRED = "asset.retired"  # Slice 4.2

    # Assignments
    ASSIGNMENT_CREATED = "assignment.created"  # Slice 5.1
    ASSIGNMENT_RETURNED = "assignment.returned"  # Slice 5.2

    # Bulk stock
    STOCK_ISSUED = "stock.issued"  # Slice 4.4
    STOCK_ADJUSTED = "stock.adjusted"  # Slice 4.4

    # Maintenance
    MAINTENANCE_STATUS_CHANGED = "maintenance.status_changed"  # Slices 6.2-6.3

    @classmethod
    def all(cls) -> frozenset[str]:
        return frozenset(
            value for name, value in vars(cls).items() if name.isupper() and isinstance(value, str)
        )

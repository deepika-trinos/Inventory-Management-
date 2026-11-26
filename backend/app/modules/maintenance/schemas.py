"""Request and response shapes for maintenance requests (Slice 6.1: MNT-01 to MNT-03; owner's
answers Q10, O4, O5, O8; decisions M2, M3, M7)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

MaintenancePriorityField = Literal["low", "medium", "high"]
MaintenanceStatusField = Literal["reported", "in_progress", "completed", "cancelled"]
# The list's status filter also offers "awaiting_inspection" (Slice 6.3); it is not a stored status.
MaintenanceStatusFilter = Literal["reported", "in_progress", "completed", "cancelled", "awaiting_inspection"]
InspectionOutcomeField = Literal["available", "damaged", "retired"]
# S6: INR, 0 or more, 2 decimals, at most 10 digits before the point (as P2 / I3).
RepairCost = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, description="INR, 2 decimals, 0 allowed.")]


class MaintenanceReport(BaseModel):
    """Staff report a problem with any asset that is not retired (MNT-02, M2)."""

    model_config = ConfigDict(extra="forbid")

    issue_description: str | None = Field(
        default=None, max_length=5000, description="Required; what is wrong, up to 1,000 characters."
    )
    priority: MaintenancePriorityField | None = Field(
        default=None, description='Optional: "low", "medium" or "high" (Q10: set by the IT Manager).'
    )
    reported_date: date | None = Field(
        default=None,
        description="Today by default (company timezone); earlier allowed; not in the future; "
        "not before the asset was created.",
    )


class MyMaintenanceReport(BaseModel):
    """An Employee reports a problem with an asset they hold now (MNT-01, M3). No priority and no
    date: the priority is set by the IT Manager (Q10) and the date is today (O5)."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(ge=1, description="The id of an asset you hold now.")
    issue_description: str | None = Field(
        default=None, max_length=5000, description="Required; what is wrong, up to 1,000 characters."
    )


class MaintenanceAssetSummary(BaseModel):
    id: int
    asset_code: str
    name: str
    serial_number: str
    status: str = Field(description="The asset's status now (reporting does not change it, Q9).")


class MaintenanceReporter(BaseModel):
    id: int
    email: str
    role: str


class MaintenanceRequestRead(BaseModel):
    """One maintenance request as Admin and IT Manager see it."""

    id: int
    request_number: str = Field(description="MNT-000001 ..., made by the system.")
    asset: MaintenanceAssetSummary
    issue_description: str
    priority: MaintenancePriorityField | None
    status: MaintenanceStatusField
    reported_date: date
    reported_by: MaintenanceReporter
    created_at: datetime = Field(description="When the request was saved (UTC).")
    # Slice 6.2 (U1): progress. Empty until each step happens.
    started_date: date | None = None
    started_at: datetime | None = None
    started_by: MaintenanceReporter | None = None
    service_provider: str | None = None
    repair_notes: str | None = None
    cost: Decimal | None = Field(default=None, description="INR, 2 decimals.")
    completion_date: date | None = None
    completed_at: datetime | None = None
    completed_by: MaintenanceReporter | None = None
    cancelled_at: datetime | None = None
    cancelled_by: MaintenanceReporter | None = None
    cancel_reason: str | None = None
    # Slice 6.3: the inspection after the repair.
    awaiting_inspection: bool = Field(
        default=False, description="Work started, Completed or Cancelled, and not yet inspected."
    )
    inspection_outcome: InspectionOutcomeField | None = None
    inspection_date: date | None = None
    inspection_notes: str | None = None
    inspected_at: datetime | None = None
    inspected_by: MaintenanceReporter | None = None


class MaintenanceHistoryEntry(BaseModel):
    """One audit row about this request (S13, U6)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    created_at: datetime
    actor: "MaintenanceActor | None"
    before: dict[str, Any] | None
    after: dict[str, Any] | None


class MaintenanceActor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class MaintenanceRequestDetail(MaintenanceRequestRead):
    """One request with its history, newest first (Slice 6.2, U2)."""

    history: list[MaintenanceHistoryEntry]


class MaintenanceStart(BaseModel):
    """Reported -> In Progress (S1, S8, S9)."""

    model_config = ConfigDict(extra="forbid")

    started_date: date | None = Field(
        default=None, description="Today by default; earlier allowed; not in the future; not before the reported date."
    )
    service_provider: str | None = Field(default=None, max_length=1000, description="Optional, up to 200.")


class MaintenanceComplete(BaseModel):
    """In Progress -> Completed (S5-S7, S9)."""

    model_config = ConfigDict(extra="forbid")

    repair_notes: str | None = Field(default=None, max_length=5000, description="Required: what was done, up to 1,000.")
    completion_date: date | None = Field(
        default=None, description="Today by default; earlier allowed; not in the future; not before the start date."
    )
    service_provider: str | None = Field(default=None, max_length=1000, description="Optional, up to 200.")
    cost: RepairCost | None = Field(default=None, description="Optional; INR, 2 decimals, 0 allowed.")


class MaintenanceCancel(BaseModel):
    """Reported or In Progress -> Cancelled (S11)."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=5000, description="Required, up to 500.")


class MaintenanceInspect(BaseModel):
    """The inspection after a repair (Slice 6.3, MNT-07). Same field names as the return's inspection (K1)."""

    model_config = ConfigDict(extra="forbid")

    inspection_outcome: str | None = Field(
        default=None, max_length=50, description='Required: "available", "damaged" or "retired".'
    )
    inspection_date: date | None = Field(
        default=None,
        description="Today by default; earlier allowed; not in the future; not before the completion date "
        "(or the day the request was cancelled).",
    )
    condition_notes: str | None = Field(
        default=None, max_length=5000,
        description="Up to 1,000; required for Damaged and Retired (for Retired they are the reason, up to 500).",
    )


class MaintenanceUpdate(BaseModel):
    """Edit while the request is open (S6, S9, S10, S12). Send only what changes; null clears."""

    model_config = ConfigDict(extra="forbid")

    priority: MaintenancePriorityField | None = None
    service_provider: str | None = Field(default=None, max_length=1000)
    repair_notes: str | None = Field(default=None, max_length=5000)
    cost: RepairCost | None = None


MaintenanceHistoryEntry.model_rebuild()


class MaintenanceRequestPage(BaseModel):
    items: list[MaintenanceRequestRead]
    total: int
    page: int
    page_size: int


class MyMaintenanceRequestRead(BaseModel):
    """What an Employee gets back after reporting (M3): the request number, the asset, the issue,
    status and date. The full My Requests page is Slice 6.4."""

    request_number: str
    asset: MaintenanceAssetSummary
    issue_description: str
    status: MaintenanceStatusField
    reported_date: date


class MyRequestAsset(BaseModel):
    """The asset as an Employee sees it on My Requests: no status, no id (Slice 6.4)."""

    asset_code: str
    name: str
    serial_number: str


class MyRequestRow(BaseModel):
    """One of my requests (Slice 6.4, MNT-08). Only Employee-safe fields: no priority, service provider,
    repair notes, cost, staff e-mails or inspection details (N12, O8)."""

    request_number: str
    asset: MyRequestAsset
    issue_description: str
    status: MaintenanceStatusField
    reported_date: date
    started_date: date | None = Field(default=None, description="When work started.")
    completion_date: date | None = Field(default=None, description="When the repair was completed.")
    cancelled_date: date | None = Field(default=None, description="The day it was cancelled (company timezone).")
    cancel_reason: str | None = None


class OpenRequestSummary(BaseModel):
    """The asset's open request, as shown on a My Assets row (M7)."""

    model_config = ConfigDict(from_attributes=True)

    request_number: str
    status: MaintenanceStatusField
    reported_date: date

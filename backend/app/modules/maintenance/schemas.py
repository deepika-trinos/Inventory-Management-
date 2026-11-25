"""Request and response shapes for maintenance requests (Slice 6.1: MNT-01 to MNT-03; owner's
answers Q10, O4, O5, O8; decisions M2, M3, M7)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MaintenancePriorityField = Literal["low", "medium", "high"]
MaintenanceStatusField = Literal["reported", "in_progress", "completed", "cancelled"]


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


class OpenRequestSummary(BaseModel):
    """The asset's open request, as shown on a My Assets row (M7)."""

    model_config = ConfigDict(from_attributes=True)

    request_number: str
    status: MaintenanceStatusField
    reported_date: date

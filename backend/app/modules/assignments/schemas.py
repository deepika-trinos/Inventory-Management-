"""Response shapes for assignment history and overdue returns (Slice 5.3: ASN-07, ASN-08, EMP-04;
owner's answers N7, N8, N12). All read-only."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.assets.schemas import AssetEmployeeSummary, AssetUserSummary


class AssignmentAssetSummary(BaseModel):
    id: int
    asset_code: str
    name: str
    serial_number: str
    status: str = Field(description="The asset's status now.")


class MyAssignmentRead(BaseModel):
    """One assignment as an Employee sees it on My Assets (N8, N12): no condition notes and no
    staff e-mails."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset: AssignmentAssetSummary
    assignment_date: date
    expected_return_date: date | None
    return_date: date | None = Field(description="Empty while the asset is still held.")
    return_outcome: str | None = Field(description="Inspection outcome on return: available / under_maintenance / damaged.")
    is_open: bool = Field(description="True while the asset is still held (not returned).")
    is_overdue: bool = Field(description="N7: expected return date before today (company timezone) and not returned.")
    days_overdue: int = Field(description="Days past the expected return date; 0 when not overdue.")


class AssignmentRead(MyAssignmentRead):
    """One assignment as Admin and IT Manager see it (employee page, overdue list)."""

    employee: AssetEmployeeSummary
    assigned_by: AssetUserSummary
    created_at: datetime = Field(description="When the assignment was saved (UTC).")
    condition_notes: str | None
    returned_by: AssetUserSummary | None
    returned_at: datetime | None = Field(description="When the return was saved (UTC).")


class EmployeeAssignments(BaseModel):
    """EMP-04: what the employee holds now and what they held before (ASN-07)."""

    employee: AssetEmployeeSummary
    current: list[AssignmentRead] = Field(description="Still held, by assignment date (oldest first).")
    past: list[AssignmentRead] = Field(description="Returned, newest return first.")


class MyAssignments(BaseModel):
    """N8: the logged-in Employee's own current and past assignments."""

    employee: AssetEmployeeSummary
    current: list[MyAssignmentRead]
    past: list[MyAssignmentRead]


class OverduePage(BaseModel):
    items: list[AssignmentRead]
    total: int
    page: int
    page_size: int

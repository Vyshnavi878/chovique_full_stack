from typing import List, Optional, Any, Literal
from pydantic import BaseModel, ConfigDict, field_validator


class ReportQueryRequest(BaseModel):
    report_type: Literal['sales', 'orders', 'products', 'customers', 'coupons', 'reward_coins']
    start_date: str
    end_date: str
    page: int = 1
    limit: int = 50

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_string(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Date is required.")
        return v.strip()


class ReportKPICard(BaseModel):
    title: str
    value: str
    growth_percentage: Optional[float] = None
    subtext: Optional[str] = None


class ReportChartPoint(BaseModel):
    label: str
    value: float
    secondary_value: Optional[float] = None


class ReportResponse(BaseModel):
    report_type: str
    start_date: str
    end_date: str
    kpi_summary: List[ReportKPICard]
    chart_data: List[ReportChartPoint]
    table_headers: List[str]
    table_rows: List[List[Any]]
    totals_footer: Optional[List[Any]] = None
    total_records: int
    page: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)

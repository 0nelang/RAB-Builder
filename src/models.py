from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Literal
from datetime import datetime

ConfidenceLvl = Literal['low', 'medium', 'high']

class ParsedRoom(BaseModel):
    """Parsing result of a single room"""

    name: str = Field(..., min_length=1, max_length=100)
    length: float = Field(gt=0, le=1000, description="The length of the room")
    width: float = Field(gt=0, le=1000, description="The width of the room")
    confidence : ConfidenceLvl
    notes: str | None = None

    @field_validator('name')
    @classmethod
    def normalize_name(cls, v:str) -> str:
        return v.strip().lower()
    
    @property
    def area(self) -> float:
        return self.length * self.width
    
class HousePlanParsed(BaseModel):
    """Parsing Result of the full House Plan"""

    rooms : list[ParsedRoom] = Field(default_factory=list)
    scale : str | None = None
    warnings : list[str] = Field(default_factory=list)

    @field_validator('rooms')
    @classmethod
    def house_plan_validator(cls, v:list[ParsedRoom]) -> list[ParsedRoom]:
        if not v:
            raise ValueError("Hasil parsing tidak menemukan ruangan apapun")
        return v
    
    @property
    def totalarea(self) -> float:
        return sum(r.area for r in self.rooms)

class RABItem(BaseModel):
    room_name: str = Field(..., min_length=1, max_length=100)
    work_description: str = Field(..., min_length=1, max_length=255)
    unit: str = Field(..., min_length=1, max_length=20)  # m², m, m³, unit, ls, dll
    volume: float = Field(gt=0)
    unit_price: float = Field(ge=0)  # ge=0 supaya user boleh kosongin sementara di editor

    @field_validator('room_name', 'work_description', 'unit')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def subtotal(self) -> float:
        return round(self.volume * self.unit_price, 2)
    
class RABResult(BaseModel):
    """Hasil generate RAB lengkap untuk 1 proyek."""

    project_name: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=200)
    items: list[RABItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)

    @field_validator('items')
    @classmethod
    def items_not_empty(cls, v: list[RABItem]) -> list[RABItem]:
        if not v:
            raise ValueError("RAB harus punya minimal 1 item pekerjaan")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> float:
        return round(sum(item.subtotal for item in self.items), 2)
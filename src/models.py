from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Literal

ConfidenceLvl = Literal['Low', 'Medium', 'High']

class ParsedRoom(BaseModel):
    """Parsing result of a single room"""

    name: str = Field(..., min_length=1, max_length=100)
    length: int = Field(gt=0, le=1000, description="The length of the room")
    width: int = Field(gt=0, le=1000, description="The width of the room")
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
    warning : list[str] = Field(default_factory=list)

    @field_validator('rooms')
    @classmethod
    def house_plan_validator(cls, v:list[ParsedRoom]) -> list[ParsedRoom]:
        if not v:
            raise ValueError("Hasil parsing tidak menemukan ruangan apapun")
        return v
    
    @property
    def totalarea(self) -> float:
        return sum(r.area for r in self.rooms)

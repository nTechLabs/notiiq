from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start: datetime
    end: datetime
    source_text: str
    confidence: float = Field(ge=0, le=1)


class AnalysisResponse(BaseModel):
    text: str
    events: list[CalendarEvent]
    processed_files: int
    analysis_method: Literal["ollama"] = "ollama"

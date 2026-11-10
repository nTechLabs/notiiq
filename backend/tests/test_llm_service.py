from datetime import datetime

import pytest

from backend.app.llm_service import ExtractedEvent, _normalize_text


def test_extracted_event_rejects_invalid_time_range() -> None:
    with pytest.raises(ValueError):
        ExtractedEvent(
            title="프로젝트 회의",
            start=datetime(2026, 11, 15, 16),
            end=datetime(2026, 11, 15, 15),
            source_text="11월 15일 오후 4시 프로젝트 회의",
            confidence=0.9,
        )


def test_normalize_text_preserves_grounding_across_lines() -> None:
    source = "11월 15일\n오후 3시 프로젝트 회의"

    assert _normalize_text(source) == "11월 15일 오후 3시 프로젝트 회의"

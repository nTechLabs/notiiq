import asyncio
from datetime import datetime

import httpx
import pytest

from backend.app.llm_service import (
    ExtractedEvent,
    OllamaScheduleAnalyzer,
    _ground_source_text,
    _normalize_text,
)


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


def test_ground_source_uses_matching_ocr_lines_when_long_quote_has_error() -> None:
    ocr_text = "\n".join(
        [
            "2026-2 통합사회2 수행평가 안내",
            "주제",
            "교과 개념의 전공적 재해석",
            "일시",
            "10월 5주차",
            "'1월 1주차",
            "채점 기준",
        ]
    )
    model_source = "\n".join(
        [
            "2026-2 통합사회2 수행평가 안내",
            "주제",
            "교과 개념의 전공적 재해석",
            "일시",
            "10월 5주차",
            "'1월 1주차",
            "모델이 바꿔 쓴 문장",
        ]
    )

    assert _ground_source_text(model_source, ocr_text) == "\n".join(
        [
            "2026-2 통합사회2 수행평가 안내",
            "주제",
            "교과 개념의 전공적 재해석",
            "일시",
            "10월 5주차",
            "'1월 1주차",
        ]
    )


def test_ground_source_rejects_unrelated_model_quote() -> None:
    assert _ground_source_text(
        "통합사회2 수행평가\n10월 5주차",
        "프로젝트 회의\n11월 15일 오후 3시",
    ) is None


def test_prompt_extracts_school_assignment_topic_and_date_range() -> None:
    prompt = OllamaScheduleAnalyzer()._build_prompt(
        "\n".join(
            [
                "2026-2 통합사회2 수행평가 안내",
                "주제: 교과 개념의 전공적 재해석 (사회탐구보고서 작성)",
                "일시: 10월 5주차 ~ 11월 1주차 (수행평가 작성)",
            ]
        ),
        datetime(2026, 11, 7),
    )

    assert "수행평가, 시험, 과제, 발표" in prompt
    assert "과목명과 주제를 포함" in prompt
    assert "10월 5주차" in prompt
    assert "종일 일정" in prompt
    assert "최대 8줄" in prompt


def test_keeps_announced_assignment_even_when_period_has_ended(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ocr_text = "\n".join(
        [
            "2026-2 통합사회2 수행평가 안내",
            "주제 교과 개념의 전공적 재해석 (사회탐구보고서 작성)",
            "일시 10월 5주차 ~ 11월 1주차 (수행평가 작성)",
        ]
    )
    response_body = {
        "response": (
            '{"events":[{"title":"통합사회2 수행평가 - 교과 개념의 전공적 재해석 '
            '(사회탐구보고서 작성)","start":"2026-10-26T00:00:00",'
            '"end":"2026-11-09T00:00:00","source_text":"'
            + ocr_text.replace("\n", "\\n")
            + '","confidence":0.95}]}'
        )
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_body)

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def mock_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mock_client)

    events = asyncio.run(
        OllamaScheduleAnalyzer().extract_events(
            ocr_text,
            reference=datetime(2026, 11, 11),
        )
    )

    assert len(events) == 1
    assert events[0].title == (
        "통합사회2 수행평가 - 교과 개념의 전공적 재해석 (사회탐구보고서 작성)"
    )
    assert events[0].start == datetime(2026, 10, 26)
    assert events[0].end == datetime(2026, 11, 9)

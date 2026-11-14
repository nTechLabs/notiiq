from fastapi.testclient import TestClient

from datetime import datetime, timedelta

from backend.app.main import app, get_ocr_service, get_schedule_analyzer
from backend.app.models import CalendarEvent


class FakeOcrService:
    def read(self, image_bytes: bytes) -> list[str]:
        assert image_bytes == b"image"
        return ["11월 15일 오후 3시 프로젝트 회의"]


class FakeScheduleAnalyzer:
    def __init__(
        self,
        expected_text: str = "11월 15일 오후 3시 프로젝트 회의",
    ) -> None:
        self.expected_text = expected_text

    async def extract_events(self, text: str) -> list[CalendarEvent]:
        assert text == self.expected_text
        start = datetime(2026, 11, 15, 15)
        return [
            CalendarEvent(
                title="프로젝트 회의",
                start=start,
                end=start + timedelta(hours=1),
                source_text=text,
                confidence=0.98,
            )
        ]


def test_health_disables_cache() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_analyze_uses_memory_only_service() -> None:
    app.dependency_overrides[get_ocr_service] = lambda: FakeOcrService()
    app.dependency_overrides[get_schedule_analyzer] = lambda: FakeScheduleAnalyzer()
    try:
        response = TestClient(app).post(
            "/api/analyze",
            files={"files": ("capture.jpg", b"image", "image/jpeg")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed_files"] == 1
    assert payload["processed_text"] is False
    assert payload["analysis_method"] == "ollama"
    assert payload["events"][0]["title"] == "프로젝트 회의"


def test_analyze_accepts_text_without_an_image() -> None:
    text = "11월 15일 오후 3시 프로젝트 회의"
    app.dependency_overrides[get_schedule_analyzer] = lambda: FakeScheduleAnalyzer(text)
    try:
        response = TestClient(app).post("/api/analyze", data={"text": text})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == text
    assert payload["processed_files"] == 0
    assert payload["processed_text"] is True


def test_analyze_combines_image_and_direct_text() -> None:
    direct_text = "좋아, 그때 보자"
    combined_text = f"11월 15일 오후 3시 프로젝트 회의\n{direct_text}"
    app.dependency_overrides[get_ocr_service] = lambda: FakeOcrService()
    app.dependency_overrides[get_schedule_analyzer] = lambda: FakeScheduleAnalyzer(combined_text)
    try:
        response = TestClient(app).post(
            "/api/analyze",
            data={"text": direct_text},
            files={"files": ("capture.jpg", b"image", "image/jpeg")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == combined_text
    assert payload["processed_files"] == 1
    assert payload["processed_text"] is True


def test_analyze_rejects_empty_input() -> None:
    response = TestClient(app).post("/api/analyze", data={"text": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "이미지 또는 텍스트를 입력하세요."


def test_analyze_rejects_non_image() -> None:
    response = TestClient(app).post(
        "/api/analyze",
        files={"files": ("message.txt", b"text", "text/plain")},
    )

    assert response.status_code == 415


def test_download_calendar_returns_ics_attachment() -> None:
    event = {
        "title": "프로젝트 회의",
        "start": "2026-11-15T15:00:00",
        "end": "2026-11-15T16:00:00",
        "source_text": "11월 15일 오후 3시 프로젝트 회의",
    }
    response = TestClient(app).post("/api/calendar", data=event)
    repeated_response = TestClient(app).post("/api/calendar", data=event)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert response.headers["content-disposition"] == 'attachment; filename="notiiq-event.ics"'
    assert "SUMMARY:프로젝트 회의" in response.text
    assert "DESCRIPTION:" not in response.text
    assert "SEQUENCE:0" in response.text
    assert "METHOD:PUBLISH" in response.text

    uid = next(line for line in response.text.splitlines() if line.startswith("UID:"))
    repeated_uid = next(
        line for line in repeated_response.text.splitlines() if line.startswith("UID:")
    )
    assert uid == repeated_uid

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .llm_service import (
    OllamaResponseError,
    OllamaScheduleAnalyzer,
    OllamaTimeoutError,
    OllamaUnavailableError,
    get_schedule_analyzer,
)
from .models import AnalysisResponse, CalendarEvent
from .ocr_service import OcrService, get_ocr_service

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_TEXT_LENGTH = 20_000
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

app = FastAPI(title="Notiiq API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7173", "http://127.0.0.1:7173"],
    allow_origin_regex=(
        r"^http://(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}):7173$"
    ),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def disable_sensitive_response_caching(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _escape_ics(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _ics_date(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def _event_uid(title: str, start: datetime, end: datetime) -> str:
    value = f"{title.strip()}\n{start.isoformat()}\n{end.isoformat()}".encode()
    hash_value = 0x811C9DC5
    for byte in value:
        hash_value ^= byte
        hash_value = (hash_value * 0x01000193) & 0xFFFFFFFF
    return f"{hash_value:08x}@notiiq.local"


@app.post("/api/calendar")
async def download_calendar(
    title: Annotated[str, Form(min_length=1, max_length=200)],
    start: Annotated[datetime, Form()],
    end: Annotated[datetime, Form()],
    source_text: Annotated[str, Form(max_length=5_000)],
) -> Response:
    event = CalendarEvent(
        title=title,
        start=start,
        end=end,
        source_text=source_text,
        confidence=1,
    )
    content = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Notiiq//Conversation Schedule//KO",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{_event_uid(event.title, event.start, event.end)}",
            f"DTSTAMP:{_ics_date(datetime.now())}",
            "SEQUENCE:0",
            "STATUS:CONFIRMED",
            f"DTSTART:{_ics_date(event.start)}",
            f"DTEND:{_ics_date(event.end)}",
            f"SUMMARY:{_escape_ics(event.title)}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="notiiq-event.ics"'},
    )


async def _validated_images(files: list[UploadFile]) -> AsyncIterator[bytes]:
    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"{file.filename or '파일'}은 지원하지 않는 이미지 형식입니다.",
            )

        content = await file.read(MAX_FILE_SIZE + 1)
        await file.close()
        if not content:
            raise HTTPException(status_code=400, detail="빈 이미지 파일은 처리할 수 없습니다.")
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"{file.filename or '파일'}의 크기가 10MB를 초과합니다.",
            )
        yield content


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_inputs(
    files: list[UploadFile] | None = File(default=None),
    text: str | None = Form(default=None, max_length=MAX_TEXT_LENGTH),
    ocr_service: OcrService = Depends(get_ocr_service),
    schedule_analyzer: OllamaScheduleAnalyzer = Depends(get_schedule_analyzer),
) -> AnalysisResponse:
    uploaded_files = files or []
    submitted_text = text.strip() if text else ""
    if not uploaded_files and not submitted_text:
        raise HTTPException(status_code=400, detail="이미지 또는 텍스트를 입력하세요.")
    if len(uploaded_files) > 20:
        raise HTTPException(status_code=400, detail="한 번에 최대 20개까지 처리할 수 있습니다.")

    lines: list[str] = []
    try:
        async for image in _validated_images(uploaded_files):
            lines.extend(ocr_service.read(image))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    input_parts = ["\n".join(line.strip() for line in lines if line.strip())]
    if submitted_text:
        input_parts.append(submitted_text)
    analysis_text = "\n".join(part for part in input_parts if part)

    try:
        events = await schedule_analyzer.extract_events(analysis_text)
    except OllamaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OllamaTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except OllamaResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnalysisResponse(
        text=analysis_text,
        events=events,
        processed_files=len(uploaded_files),
        processed_text=bool(submitted_text),
    )

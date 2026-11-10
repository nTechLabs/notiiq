import re
from datetime import datetime, timedelta

from .models import CalendarEvent

EVENT_KEYWORDS = (
    "회의",
    "미팅",
    "약속",
    "예약",
    "일정",
    "모임",
    "병원",
    "식사",
    "면접",
    "수업",
    "공연",
    "상담",
    "방문",
    "출발",
    "도착",
    "여행",
    "행사",
    "생일",
    "결혼",
    "주차",
)

DATE_PATTERN = re.compile(
    r"(?:(?P<year>20\d{2})[년./-]\s*)?"
    r"(?P<month>1[0-2]|0?[1-9])[월./-]\s*"
    r"(?P<day>3[01]|[12]\d|0?[1-9])일?"
    r"(?:\s*(?P<weekday>[월화수목금토일](?:요일)?))?"
    r"(?:\s*(?P<ampm>오전|오후|AM|PM|am|pm))?"
    r"(?:\s*(?P<hour>2[0-3]|[01]?\d)(?:[:시]\s*(?P<minute>[0-5]?\d)?분?)?)?"
)
DATE_TEXT_PATTERN = re.compile(
    r"(?:(?:20\d{2})[년./-]\s*)?"
    r"(?:1[0-2]|0?[1-9])[월./-]\s*(?:3[01]|[12]\d|0?[1-9])일?"
)
TIME_TEXT_PATTERN = re.compile(
    r"(?:(?:오전|오후|AM|PM|am|pm)\s*)?"
    r"(?:2[0-3]|[01]?\d)(?:[:시]\s*(?:[0-5]?\d)?분?)"
)
TEMPORAL_WORD_PATTERN = re.compile(
    r"\b(?:월요일|화요일|수요일|목요일|금요일|토요일|일요일|"
    r"오전|오후|AM|PM|am|pm)\b"
)
CHAT_METADATA_PATTERN = re.compile(
    r"^(?:읽음|사진|이모티콘|채팅방|메시지|삭제된 메시지|"
    r"\d+(?:분|시간|일) 전)$"
)
CHAT_DATE_HEADER_PATTERN = re.compile(
    r"^20\d{2}년\s*(?:1[0-2]|0?[1-9])월\s*"
    r"(?:3[01]|[12]\d|0?[1-9])일\s*"
    r"(?:월요일|화요일|수요일|목요일|금요일|토요일|일요일)$"
)
CHAT_TIMESTAMP_PATTERN = re.compile(
    r"^(?:오전|오후)\s*(?:1[0-2]|0?[1-9]):[0-5]\d$"
)
TITLE_WINDOW_BEFORE = 2
TITLE_WINDOW_AFTER = 3


def _clean_title_candidate(line: str) -> str:
    candidate = DATE_TEXT_PATTERN.sub(" ", line)
    candidate = TIME_TEXT_PATTERN.sub(" ", candidate)
    candidate = TEMPORAL_WORD_PATTERN.sub(" ", candidate)
    candidate = re.sub(r"\b20\d{2}년\b", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -:,.·'\"")
    return candidate


def _title_score(candidate: str, distance: int) -> int:
    score = max(0, 4 - distance)
    if any(keyword in candidate for keyword in EVENT_KEYWORDS):
        score += 10
    if 2 <= len(candidate) <= 40:
        score += 4
    if re.search(r"[가-힣A-Za-z]{2,}", candidate):
        score += 3
    if len(candidate) > 80:
        score -= 5
    return score


def _event_title(lines: list[str], date_index: int) -> str:
    start = max(0, date_index - TITLE_WINDOW_BEFORE)
    end = min(len(lines), date_index + TITLE_WINDOW_AFTER + 1)
    candidates: list[tuple[int, int, str]] = []

    for index in range(start, end):
        if (
            CHAT_DATE_HEADER_PATTERN.fullmatch(lines[index])
            or CHAT_TIMESTAMP_PATTERN.fullmatch(lines[index])
        ):
            continue
        candidate = _clean_title_candidate(lines[index])
        if not candidate or CHAT_METADATA_PATTERN.fullmatch(candidate):
            continue
        if not re.search(r"[가-힣A-Za-z]", candidate):
            continue

        distance = abs(index - date_index)
        candidates.append((_title_score(candidate, distance), -distance, candidate))

    if not candidates:
        return "일정"
    return max(candidates)[2][:200]


def _parse_start(match: re.Match[str], reference: datetime) -> datetime | None:
    year = int(match.group("year") or reference.year)
    month = int(match.group("month"))
    day = int(match.group("day"))
    hour = int(match.group("hour") or 9)
    minute = int(match.group("minute") or 0)
    ampm = (match.group("ampm") or "").lower()

    if ampm in {"오후", "pm"} and hour < 12:
        hour += 12
    elif ampm in {"오전", "am"} and hour == 12:
        hour = 0

    try:
        start = datetime(year, month, day, hour, minute)
    except ValueError:
        return None

    if match.group("year") is None and start < reference - timedelta(days=30):
        start = start.replace(year=year + 1)
    return start


def extract_events(text: str, reference: datetime | None = None) -> list[CalendarEvent]:
    reference = reference or datetime.now()
    events: list[CalendarEvent] = []
    seen: set[tuple[str, datetime]] = set()
    lines = [raw_line.strip() for raw_line in text.splitlines() if raw_line.strip()]

    for index, line in enumerate(lines):
        if CHAT_DATE_HEADER_PATTERN.fullmatch(line):
            continue
        if DATE_TEXT_PATTERN.search(line) is None:
            continue

        context_lines = [
            context_line
            for context_line in lines[index : index + TITLE_WINDOW_AFTER + 1]
            if not CHAT_DATE_HEADER_PATTERN.fullmatch(context_line)
            and not CHAT_TIMESTAMP_PATTERN.fullmatch(context_line)
        ]
        joined_lines = " ".join(context_lines)
        match = DATE_PATTERN.search(joined_lines)
        if match is None:
            continue

        start = _parse_start(match, reference)
        if start is None:
            continue

        title = _event_title(lines, index)
        key = (title, start)
        if key in seen:
            continue
        seen.add(key)

        context = " ".join(context_lines)
        has_keyword = any(keyword in title for keyword in EVENT_KEYWORDS)
        has_time = match.group("hour") is not None
        confidence = 0.9 if has_keyword and has_time else 0.75 if has_time else 0.6
        events.append(
            CalendarEvent(
                title=title,
                start=start,
                end=start + timedelta(hours=1),
                source_text=context,
                confidence=confidence,
            )
        )
    return sorted(events, key=lambda event: event.start)

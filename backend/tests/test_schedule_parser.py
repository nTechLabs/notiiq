from datetime import datetime

from backend.app.schedule_parser import extract_events


def test_extracts_korean_schedule_with_time() -> None:
    events = extract_events(
        "11월 15일 오후 3시 강남역에서 프로젝트 회의",
        reference=datetime(2026, 11, 10),
    )

    assert len(events) == 1
    assert events[0].start == datetime(2026, 11, 15, 15, 0)
    assert events[0].end == datetime(2026, 11, 15, 16, 0)
    assert events[0].confidence == 0.9


def test_rolls_implicit_year_forward() -> None:
    events = extract_events(
        "1월 5일 오전 10시 병원 예약",
        reference=datetime(2026, 11, 10),
    )

    assert events[0].start == datetime(2027, 1, 5, 10, 0)


def test_ignores_invalid_date() -> None:
    assert extract_events("2월 31일 오후 2시 회의") == []


def test_uses_nearby_schedule_text_instead_of_weekday() -> None:
    events = extract_events(
        "1월 7일 토요일\n오전 9시\n승주 주차 예약",
        reference=datetime(2026, 11, 10),
    )

    assert events[0].title == "승주 주차 예약"
    assert events[0].start == datetime(2027, 1, 7, 9, 0)


def test_uses_nearby_title_when_ampm_is_separate_line() -> None:
    events = extract_events(
        "프로젝트 발표\n11월 17일\n오후 2시",
        reference=datetime(2026, 11, 10),
    )

    assert events[0].title == "프로젝트 발표"
    assert events[0].start == datetime(2026, 11, 17, 14, 0)


def test_ignores_chat_date_header_and_message_timestamps() -> None:
    text = "\n".join(
        [
            "이거 해석해줘",
            "오후 11:17",
            "2026년 11월 7일 토요일",
            "문현승",
            "일상적인 대화 내용",
            "오전 1:54",
        ]
    )

    assert extract_events(text, reference=datetime(2026, 11, 10)) == []


def test_does_not_use_chat_timestamp_as_event_time() -> None:
    events = extract_events(
        "11월 15일 프로젝트 회의\n오후 11:17",
        reference=datetime(2026, 11, 10),
    )

    assert events[0].title == "프로젝트 회의"
    assert events[0].start == datetime(2026, 11, 15, 9, 0)

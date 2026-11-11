# Notiiq 제품 아이디어

## 목표

Notiiq는 메신저 대화와 학교 안내문 캡처에서 일정을 찾아, 사용자가 검토한 뒤 휴대폰이나 PC 캘린더에 등록할 수 있게 하는 로컬 우선 웹 애플리케이션이다.

약속뿐 아니라 날짜나 기간이 명시된 수행평가, 시험, 과제, 발표, 제출 안내도 일정 후보로 다룬다. OCR 오인식이 있더라도 로컬 AI가 과목명, 주제, 날짜 문맥을 함께 분석해 사람이 이해할 수 있는 일정 제목과 기간을 만든다.

## 현재 사용자 흐름

1. 사용자가 JPG, PNG, WEBP 캡처를 최대 20장까지 선택한다.
2. FastAPI가 이미지를 메모리에서만 읽고 EasyOCR로 한국어와 영어 텍스트를 추출한다.
3. 로컬 Ollama `qwen3:8b`가 약속과 학교 공지를 분석해 제목, 시작·종료 시각, 원문 근거, 신뢰도를 반환한다.
4. 서버가 모델의 원문 근거를 실제 OCR 텍스트와 다시 대조하고 중복이나 근거 없는 결과를 제거한다.
5. 사용자가 일정 제목과 인식 결과를 확인한 후 원하는 일정만 캘린더 등록 버튼을 누른다.
6. Android는 제목과 일시가 채워진 Google Calendar 등록 화면을 열고, iPhone·iPad·PC는 `.ics` 파일을 공유하거나 다운로드한다.
7. 캘린더에는 제목과 일시만 전달하며 OCR 원문과 분석 세부 내용은 설명으로 저장하지 않는다.

## 개인정보 원칙

- 업로드 이미지와 OCR 텍스트를 파일, 데이터베이스, 브라우저 저장소, 애플리케이션 로그에 보관하지 않는다.
- OCR 텍스트는 `127.0.0.1`에서 실행되는 로컬 Ollama에만 전달한다.
- API 응답은 캐시하지 않는다.
- 사용자의 명시적인 클릭 전에는 캘린더 등록 동작을 시작하지 않는다.
- 캘린더 저장 화면에서도 OCR 원문과 상세 분석 내용은 제외한다.

## 기술 구성

- Backend: Python 3.12, FastAPI, Pydantic
- OCR: EasyOCR, PyTorch CPU, OpenCV
- 일정 분석: Ollama `qwen3:8b`, JSON Schema 구조화 출력
- Frontend: React, TypeScript, Vite
- 검증: Pytest, Vitest, oxlint, TypeScript/Vite production build

## 역할

- `FE`: 이미지 업로드, 결과 검토, Android Google Calendar 연결, `.ics` 생성
- `BE`: 업로드 검증, EasyOCR, Ollama 일정 분석, 원문 근거 검증, 캘린더 API
- `QA`: OCR·API·UI·캘린더 결과·개인정보 비저장 회귀 검증

## 다음 개선 후보

- 일정 장소를 별도 필드로 추출하고 캘린더의 장소 필드에만 저장
- 사용자가 시작·종료 시각과 장소를 수정할 수 있는 검토 UI
- 상대 날짜와 불명확한 주차 표현의 정확도 향상
- OCR 영역 정렬 및 학교 안내문 표 인식 개선
- OAuth와 토큰 저장 정책을 설계한 후 Google Calendar 또는 Microsoft Calendar API 직접 연동

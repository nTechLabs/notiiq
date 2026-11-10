# Notiiq

대화 캡처 이미지에서 OCR로 텍스트를 추출하고, 날짜와 시간이 포함된 일정 후보를 찾아 사용자가 확인한 일정을 캘린더에 등록하는 웹 애플리케이션입니다.

업로드한 이미지와 OCR 텍스트는 요청을 처리하는 동안 메모리에서만 사용하며 파일, 데이터베이스, 브라우저 저장소에 보관하지 않습니다.

## 주요 기능

- JPG, PNG, WEBP 대화 캡처 업로드 및 드래그 앤 드롭
- 한 번에 최대 20개 이미지 처리
- EasyOCR 기반 한국어/영어 텍스트 인식
- Ollama `qwen3:8b` 로컬 AI 기반 일정 문맥 및 제목 추출
- 일정 제목, 시작 시간, 종료 시간, 인식 신뢰도 표시
- 사용자가 확인한 일정만 `.ics` 캘린더 파일로 생성
- 업로드 이미지 및 OCR 텍스트 비저장
- 모바일 화면과 키보드 탐색 지원

## 기술 구성

| 구분 | 기술 |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Pydantic |
| OCR | EasyOCR, PyTorch CPU, OpenCV |
| Local AI | Ollama, qwen3:8b |
| Test | Pytest |
| Python | 3.12 |

## 프로젝트 구조

```text
notiiq/
├─ .github/
│  └─ agents/
│     ├─ BE.agent.md
│     ├─ FE.agent.md
│     └─ QA.agent.md
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ models.py
│  │  ├─ ocr_service.py
│  │  └─ schedule_parser.py
│  └─ tests/
├─ capture/
├─ frontend/
│  ├─ src/
│  ├─ package.json
│  └─ vite.config.ts
├─ requirements.txt
└─ workflow.md
```

`capture` 디렉터리에는 로컬 OCR 검증에 사용할 테스트 캡처가 들어 있습니다. 실제 대화 내용이 포함될 수 있으므로 외부로 공유하거나 테스트 출력에 기록하지 마세요.

## 사전 요구사항

- Windows
- Python 3.12
- Node.js 20 이상
- npm
- Ollama 0.40 이상
- Ollama 모델 `qwen3:8b`

현재 프로젝트는 CPU 환경을 기준으로 구성되어 있으므로 CUDA GPU가 없어도 실행할 수 있습니다.

Ollama 모델 준비:

```powershell
ollama pull qwen3:8b
ollama serve
```

Ollama 데스크톱 앱이 실행 중이면 별도로 `ollama serve`를 실행할 필요가 없습니다.

`qwen3:8b`는 일정 추출 시 사고 모드를 사용하지 않으며, CPU 환경의 긴 OCR 입력을 위해 최대 10분까지 응답을 기다립니다. 분석 시간이 초과되면 한 번에 처리하는 이미지 수를 줄이세요.

## 설치

### 1. Python 가상환경

프로젝트 루트에서 다음 명령을 실행합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

PowerShell 실행 정책 때문에 가상환경을 활성화할 수 없다면 활성화 없이 다음과 같이 실행할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Frontend 의존성

```powershell
Set-Location frontend
npm install
Set-Location ..
```

## 실행

Backend와 Frontend를 서로 다른 터미널에서 실행합니다.

### Backend

프로젝트 루트에서:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend 상태 확인:

```text
http://127.0.0.1:8000/api/health
```

FastAPI API 문서:

```text
http://127.0.0.1:8000/docs
```

### Frontend

별도 터미널에서:

```powershell
Set-Location frontend
npm run dev
```

브라우저에서 다음 주소를 엽니다.

```text
http://localhost:7173
```

Vite 개발 서버는 `/api` 요청을 `http://127.0.0.1:8000`으로 전달합니다.

### 휴대폰에서 접속

PC와 휴대폰을 같은 Wi-Fi에 연결한 후 휴대폰 브라우저에서 다음 주소를 엽니다.

```text
http://192.168.0.128:7173
```

Vite는 `0.0.0.0:7173`에서 요청을 수신하도록 설정되어 있습니다. PC의 IP가 DHCP로 변경되면 다음 명령으로 현재 IPv4 주소를 다시 확인하세요.

```powershell
Get-NetIPConfiguration |
  Where-Object { $_.IPv4DefaultGateway -ne $null } |
  Select-Object -ExpandProperty IPv4Address
```

접속되지 않으면 Windows 방화벽에서 Node.js 또는 TCP 7173 포트의 개인 네트워크 접근을 허용해야 합니다. 공용 네트워크에는 포트를 개방하지 않는 것을 권장합니다.

## 사용 방법

1. `대화 캡처 선택 또는 끌어놓기` 영역을 누르거나 이미지를 드래그합니다.
2. 하단 목록에서 선택된 이미지와 파일명을 확인합니다.
3. 잘못 선택한 이미지는 썸네일의 `×` 버튼으로 제거합니다.
4. `이미지에서 일정 찾기` 버튼을 누릅니다.
5. OCR 처리 후 표시된 일정 제목과 날짜 및 시간을 확인합니다.
6. 등록할 일정의 `기본 캘린더로 열기` 버튼을 누릅니다.
7. 모바일 공유 시트에서 기본 캘린더 앱을 선택하고 일정 저장을 승인합니다.

모바일 브라우저가 캘린더 파일 공유를 지원하지 않으면 `.ics` 파일이 다운로드됩니다. 다운로드 알림에서 파일을 열고 기본 캘린더 앱을 선택하세요. 웹 브라우저 보안 정책상 사용자 승인 없이 캘린더에 일정을 직접 저장할 수는 없습니다.

PC에서는 버튼을 누르면 `.ics` 파일이 바로 다운로드됩니다. Chrome 오른쪽 위의 다운로드 목록에서 해당 파일을 열면 Windows에 연결된 기본 캘린더 앱으로 전달됩니다. `.ics` 파일에 연결된 기본 앱이 없다면 Windows의 `기본 앱` 설정에서 캘린더 또는 Outlook을 연결해야 합니다.

동일한 제목, 시작 시간, 종료 시간을 가진 일정은 항상 같은 iCalendar `UID`를 사용합니다. 표준 UID 중복 처리를 지원하는 캘린더 앱에서는 같은 파일을 다시 열어도 기존 일정으로 인식합니다. 다만 일부 캘린더 앱은 파일 가져오기 시 UID를 무시하므로, 최종 저장 화면에서 동일 일정이 이미 있는지 확인해야 할 수 있습니다.

EasyOCR 한국어/영어 모델을 처음 초기화할 때는 모델 다운로드로 인해 첫 요청이 오래 걸릴 수 있습니다.

## API

### 상태 확인

```http
GET /api/health
```

응답:

```json
{
  "status": "ok"
}
```

### 이미지 분석

```http
POST /api/analyze
Content-Type: multipart/form-data
```

요청 필드:

| 필드 | 형식 | 설명 |
|---|---|---|
| `files` | 이미지 배열 | JPG, PNG, WEBP. 파일당 최대 10MB, 최대 20개 |

응답 예시:

```json
{
  "text": "OCR로 인식한 텍스트",
  "events": [
    {
      "title": "프로젝트 회의",
      "start": "2026-11-15T15:00:00",
      "end": "2026-11-15T16:00:00",
      "source_text": "일정이 포함된 원본 문장",
      "confidence": 0.9
    }
  ],
  "processed_files": 1
}
```

## 개인정보 처리 원칙

- 업로드 이미지를 서버 디스크나 데이터베이스에 저장하지 않습니다.
- 이미지는 요청 처리 중 메모리에서 OpenCV 배열로 변환됩니다.
- OCR 텍스트는 `127.0.0.1:11434`의 로컬 Ollama에만 전달됩니다.
- 기본 모델은 `qwen3:8b`이며 `OLLAMA_MODEL` 환경변수로 변경할 수 있습니다.
- OCR 텍스트를 애플리케이션 로그에 기록하지 않습니다.
- OCR 결과를 `localStorage`, `sessionStorage`, IndexedDB에 저장하지 않습니다.
- API 응답에 `Cache-Control: no-store`와 `Pragma: no-cache`를 적용합니다.
- 요청이 끝나면 업로드 이미지와 OCR 결과에 대한 메모리 참조가 폐기됩니다.
- 캘린더 파일은 사용자가 명시적으로 등록 버튼을 누른 경우에만 브라우저에서 생성됩니다.

EasyOCR 모델 파일은 사용자 환경에 캐시될 수 있지만 모델에는 업로드 이미지나 대화 내용이 포함되지 않습니다.

## 테스트 및 검증

### Backend 테스트

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Frontend lint

```powershell
Set-Location frontend
npm run lint
```

### Frontend production build

```powershell
Set-Location frontend
npm run build
```

테스트 코드에는 실제 대화 내용을 복사하지 말고 합성된 문장을 사용하세요.

## 에이전트 역할

프로젝트별 Copilot 에이전트는 `.github/agents`에 정의되어 있습니다.

| 에이전트 | 담당 |
|---|---|
| `FE` | React UI, 이미지 업로드, 일정 검토, ICS 생성 |
| `BE` | FastAPI, EasyOCR, 일정 추출, 입력 검증, 개인정보 제어 |
| `QA` | API 계약, OCR 정확도, UI 흐름, 캘린더 결과, 개인정보 회귀 테스트 |

세부 개발 단계와 인수인계 방식은 [workflow.md](workflow.md)를 참고하세요.

## 문제 해결

### `Failed to fetch` 또는 분석 서버 연결 오류

FastAPI 서버가 실행 중인지 확인합니다.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

연결할 수 없다면 프로젝트 루트에서 Backend를 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 첫 OCR 요청이 오래 걸리는 경우

EasyOCR가 한국어와 영어 모델을 처음 내려받고 PyTorch 모델을 초기화하는 과정입니다. 이후 요청에서는 초기화된 Reader를 재사용합니다.

### CPU 관련 경고가 표시되는 경우

현재 설정은 CPU 전용입니다. `Using CPU` 또는 GPU가 없다는 경고는 정상이며 OCR 실행을 막지 않습니다.

### 이미지가 분석되지 않는 경우

다음 항목을 확인합니다.

- 이미지 형식이 JPG, PNG, WEBP인지 확인
- 파일 하나의 크기가 10MB 이하인지 확인
- 한 번에 선택한 파일이 20개 이하인지 확인
- 손상된 이미지가 아닌지 확인

## 향후 개선 항목

- 자연어 일정 표현 및 상대 날짜 인식 확대
- 일정 제목과 장소 분리
- 사용자 수정 후 캘린더 등록
- OCR 결과 영역별 정렬 정확도 개선
- 개인정보 저장 정책을 유지하는 로컬 일정 분석 모델 도입
- OAuth 보안 정책 수립 후 Google Calendar 또는 Microsoft Calendar 연동

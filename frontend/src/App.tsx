import { useEffect, useMemo, useState } from 'react'
import type { ChangeEvent, DragEvent, FormEvent } from 'react'
import './App.css'

export type CalendarEvent = {
  title: string
  start: string
  end: string
  source_text: string
  confidence: number
}

type AnalysisResponse = {
  text: string
  events: CalendarEvent[]
  processed_files: number
  processed_text: boolean
  analysis_method: 'ollama'
}

function escapeIcs(value: string) {
  return value
    .replaceAll('\\', '\\\\')
    .replaceAll('\n', '\\n')
    .replaceAll(',', '\\,')
    .replaceAll(';', '\\;')
}

function icsDate(value: string) {
  return new Date(value).toISOString().replaceAll(/[-:]/g, '').replace('.000', '')
}

function eventUid(event: CalendarEvent) {
  const bytes = new TextEncoder().encode(
    `${event.title.trim()}\n${event.start}\n${event.end}`,
  )
  let hash = 0x811c9dc5
  bytes.forEach((byte) => {
    hash ^= byte
    hash = Math.imul(hash, 0x01000193) >>> 0
  })
  return `${hash.toString(16).padStart(8, '0')}@notiiq.local`
}

function createCalendarFile(event: CalendarEvent) {
  const content = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Notiiq//Conversation Schedule//KO',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${eventUid(event)}`,
    `DTSTAMP:${icsDate(new Date().toISOString())}`,
    'SEQUENCE:0',
    'STATUS:CONFIRMED',
    `DTSTART:${icsDate(event.start)}`,
    `DTEND:${icsDate(event.end)}`,
    `SUMMARY:${escapeIcs(event.title)}`,
    'END:VEVENT',
    'END:VCALENDAR',
  ].join('\r\n')

  const safeTitle = event.title.replace(/[\\/:*?"<>|]/g, '-').slice(0, 60) || 'notiiq-event'
  return new File([content], `${safeTitle}.ics`, {
    type: 'text/calendar;charset=utf-8',
  })
}

function isMobileDevice() {
  return (
    /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ||
    (/Macintosh/i.test(navigator.userAgent) && navigator.maxTouchPoints > 1)
  )
}

function isAndroidDevice() {
  return /Android/i.test(navigator.userAgent)
}

export function createGoogleCalendarUrl(event: CalendarEvent) {
  const parameters = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.title,
    dates: `${icsDate(event.start)}/${icsDate(event.end)}`,
  })
  return `https://calendar.google.com/calendar/render?${parameters.toString()}`
}

function App() {
  const [files, setFiles] = useState<File[]>([])
  const [directText, setDirectText] = useState('')
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState('')
  const [calendarMessage, setCalendarMessage] = useState('')

  const previews = useMemo(
    () => files.map((file) => ({ file, url: URL.createObjectURL(file) })),
    [files],
  )

  useEffect(
    () => () => previews.forEach(({ url }) => URL.revokeObjectURL(url)),
    [previews],
  )

  useEffect(() => {
    function preventBrowserFileOpen(event: globalThis.DragEvent) {
      event.preventDefault()
    }

    window.addEventListener('dragover', preventBrowserFileOpen)
    window.addEventListener('drop', preventBrowserFileOpen)
    return () => {
      window.removeEventListener('dragover', preventBrowserFileOpen)
      window.removeEventListener('drop', preventBrowserFileOpen)
    }
  }, [])

  function addFiles(selectedFiles: File[]) {
    const images = selectedFiles.filter((file) =>
      ['image/jpeg', 'image/png', 'image/webp'].includes(file.type),
    )

    setFiles((currentFiles) => {
      const uniqueFiles = new Map(
        [...currentFiles, ...images].map((file) => [
          `${file.name}-${file.size}-${file.lastModified}`,
          file,
        ]),
      )
      return Array.from(uniqueFiles.values()).slice(0, 20)
    })
    setAnalysis(null)
    setError(
      images.length !== selectedFiles.length
        ? 'JPG, PNG, WEBP 이미지만 목록에 추가했습니다.'
        : '',
    )
  }

  function chooseFiles(event: ChangeEvent<HTMLInputElement>) {
    addFiles(Array.from(event.target.files ?? []))
    event.target.value = ''
  }

  function dropFiles(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(false)
    addFiles(Array.from(event.dataTransfer.files))
  }

  function removeFile(fileToRemove: File) {
    setFiles((currentFiles) => currentFiles.filter((file) => file !== fileToRemove))
    setAnalysis(null)
  }

  function updateDirectText(value: string) {
    setDirectText(value)
    setAnalysis(null)
  }

  function updateEventTitle(index: number, title: string) {
    setAnalysis((currentAnalysis) => {
      if (!currentAnalysis) {
        return currentAnalysis
      }

      return {
        ...currentAnalysis,
        events: currentAnalysis.events.map((event, eventIndex) =>
          eventIndex === index ? { ...event, title } : event,
        ),
      }
    })
  }

  async function registerCalendar(
    submitEvent: FormEvent<HTMLFormElement>,
    event: CalendarEvent,
  ) {
    const calendarEvent = { ...event, title: event.title.trim() }
    const file = createCalendarFile(calendarEvent)
    setCalendarMessage('')
    setError('')

    if (isAndroidDevice()) {
      submitEvent.preventDefault()
      window.location.assign(createGoogleCalendarUrl(calendarEvent))
      return
    }

    if (
      isMobileDevice() &&
      typeof navigator.share === 'function' &&
      typeof navigator.canShare === 'function' &&
      navigator.canShare({ files: [file] })
    ) {
      submitEvent.preventDefault()
      try {
        await navigator.share({
          title: calendarEvent.title,
          text: '기본 캘린더 앱에서 이 일정을 등록해 주세요.',
          files: [file],
        })
        setCalendarMessage('캘린더 앱에서 일정 저장을 완료해 주세요.')
      } catch (reason) {
        if (reason instanceof DOMException && reason.name === 'AbortError') {
          setCalendarMessage('캘린더 등록을 취소했습니다.')
          return
        }
        setError(
          reason instanceof Error
            ? `캘린더 앱을 열지 못했습니다: ${reason.message}`
            : '캘린더 앱을 열지 못했습니다.',
        )
      }
      return
    }

    setCalendarMessage(
      isMobileDevice()
        ? '캘린더 파일 다운로드를 시작했습니다. 다운로드 알림에서 파일을 선택한 후 기본 캘린더 앱으로 등록해 주세요.'
        : 'notiiq-event.ics 다운로드를 시작했습니다. Chrome 다운로드 목록에서 파일을 열면 PC의 기본 캘린더로 등록할 수 있습니다.',
    )
  }

  async function analyze(event: FormEvent) {
    event.preventDefault()
    const submittedText = directText.trim()
    if (files.length === 0 && !submittedText) {
      setError('이미지 또는 대화 텍스트를 입력해 주세요.')
      return
    }

    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    if (submittedText) {
      formData.append('text', submittedText)
    }
    setIsLoading(true)
    setError('')
    try {
      const response = await fetch('/api/analyze', { method: 'POST', body: formData })
      const payload = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(payload?.detail ?? `입력 내용을 분석하지 못했습니다. (${response.status})`)
      }
      setAnalysis(payload)
    } catch (reason) {
      setError(
        reason instanceof TypeError
          ? '분석 서버에 연결할 수 없습니다. FastAPI 서버가 실행 중인지 확인해 주세요.'
          : reason instanceof Error
            ? reason.message
            : '알 수 없는 오류가 발생했습니다.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  const hasDirectText = directText.trim().length > 0

  return (
    <main>
      <header>
        <p className="eyebrow">PRIVATE SCHEDULE ASSISTANT</p>
        <h1>대화 내용에서<br />일정만 꺼내세요.</h1>
        <p className="lead">
          캡처 이미지는 메모리에서 OCR 처리되고, 직접 입력한 텍스트와 함께 로컬 AI가 일정 문맥을 분석합니다.
          데이터는 PC 밖으로 전송되거나 서버에 저장되지 않습니다.
        </p>
      </header>

      <form className="upload-card" onSubmit={analyze}>
        <label
          className={`drop-zone${isDragging ? ' is-dragging' : ''}`}
          onDragEnter={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
              setIsDragging(false)
            }
          }}
          onDrop={dropFiles}
        >
          <span className="upload-icon">+</span>
          <strong>대화 캡처 선택 또는 끌어놓기</strong>
          <small>JPG, PNG, WEBP · 파일당 최대 10MB · 최대 20장</small>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={chooseFiles}
          />
        </label>

        {previews.length > 0 && (
          <div className="preview-strip" aria-label="선택한 이미지">
            {previews.map(({ file, url }) => (
              <div className="preview-item" key={`${file.name}-${file.lastModified}`}>
                <img src={url} alt="" />
                <span title={file.name}>{file.name}</span>
                <button
                  type="button"
                  aria-label={`${file.name} 제거`}
                  onClick={() => removeFile(file)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="input-divider"><span>또는</span></div>

        <label className="text-input">
          <strong>대화 텍스트 직접 입력</strong>
          <textarea
            value={directText}
            maxLength={20000}
            placeholder="일정이 포함된 대화나 안내문 내용을 붙여 넣으세요."
            onChange={(event) => updateDirectText(event.target.value)}
          />
          <small>{directText.length.toLocaleString()} / 20,000자</small>
        </label>

        <button
          className="primary"
          type="submit"
          disabled={isLoading || (files.length === 0 && !hasDirectText)}
        >
          {isLoading
            ? '일정 분석 중…'
            : files.length > 0
              ? `${files.length}개 이미지${hasDirectText ? '와 텍스트' : ''}에서 일정 찾기`
              : hasDirectText
                ? '텍스트에서 일정 찾기'
                : '이미지 또는 텍스트에서 일정 찾기'}
        </button>
        {error && <p className="error" role="alert">{error}</p>}
      </form>

      {analysis && (
        <section className="results">
          <div className="section-heading">
            <div>
              <p className="eyebrow">ANALYSIS RESULT</p>
              <h2>찾은 일정 {analysis.events.length}개</h2>
            </div>
            <span>
              {analysis.processed_files > 0 && `${analysis.processed_files}개 이미지 · `}
              {analysis.processed_text && '직접 입력 텍스트 · '}
              로컬 AI 분석 완료
            </span>
          </div>

          {analysis.events.length === 0 ? (
            <div className="empty">
              날짜가 포함된 일정을 찾지 못했습니다. 분석 텍스트를 확인해 주세요.
            </div>
          ) : (
            <div className="event-list">
              {analysis.events.map((event, index) => (
                <article className="event-card" key={`${event.start}-${index}`}>
                  <div className="date-block">
                    <strong>
                      {new Intl.DateTimeFormat('ko-KR', { day: 'numeric' }).format(new Date(event.start))}
                    </strong>
                    <span>
                      {new Intl.DateTimeFormat('ko-KR', { month: 'short' }).format(new Date(event.start))}
                    </span>
                  </div>
                  <div className="event-copy">
                    <label>
                      일정 제목
                      <input
                        type="text"
                        value={event.title}
                        maxLength={200}
                        onChange={(changeEvent) => updateEventTitle(index, changeEvent.target.value)}
                      />
                    </label>
                    <p>
                      {new Intl.DateTimeFormat('ko-KR', {
                        dateStyle: 'long',
                        timeStyle: 'short',
                      }).format(new Date(event.start))}
                    </p>
                    <small>인식 신뢰도 {Math.round(event.confidence * 100)}%</small>
                  </div>
                  <form
                    className="calendar-form"
                    method="POST"
                    action="/api/calendar"
                    onSubmit={(submitEvent) => void registerCalendar(submitEvent, event)}
                  >
                    <input type="hidden" name="title" value={event.title.trim()} />
                    <input type="hidden" name="start" value={event.start} />
                    <input type="hidden" name="end" value={event.end} />
                    <input type="hidden" name="source_text" value={event.source_text} />
                    <button
                      type="submit"
                      className="calendar-button"
                      disabled={!event.title.trim()}
                    >
                      {isAndroidDevice() ? 'Google 캘린더에 추가' : '기본 캘린더로 열기'}
                    </button>
                  </form>
                </article>
              ))}
            </div>
          )}

          {calendarMessage && (
            <div className="calendar-message" role="status">
              <span>{calendarMessage}</span>
              <button type="button" onClick={() => setCalendarMessage('')} aria-label="안내 닫기">
                ×
              </button>
            </div>
          )}

          <details>
            <summary>분석 텍스트 확인</summary>
            <pre>{analysis.text}</pre>
          </details>
        </section>
      )}

      <footer>
        <strong>대화 내용 비저장 원칙</strong>
        <span>업로드 이미지와 입력·OCR 텍스트는 요청 처리 후 메모리에서 폐기됩니다.</span>
      </footer>
    </main>
  )
}

export default App

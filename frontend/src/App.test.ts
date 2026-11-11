import { describe, expect, it } from 'vitest'
import { createGoogleCalendarUrl } from './App'

describe('Android Google Calendar registration', () => {
  it('creates a prefilled Google Calendar event URL', () => {
    const url = new URL(
      createGoogleCalendarUrl({
        title: '통합사회2 수행평가',
        start: '2026-10-26T00:00:00+09:00',
        end: '2026-11-09T00:00:00+09:00',
        source_text: '교과 개념의 전공적 재해석',
        confidence: 0.95,
      }),
    )

    expect(url.origin).toBe('https://calendar.google.com')
    expect(url.pathname).toBe('/calendar/render')
    expect(url.searchParams.get('action')).toBe('TEMPLATE')
    expect(url.searchParams.get('text')).toBe('통합사회2 수행평가')
    expect(url.searchParams.get('dates')).toBe(
      '20261025T150000Z/20261108T150000Z',
    )
    expect(url.searchParams.has('details')).toBe(false)
  })
})

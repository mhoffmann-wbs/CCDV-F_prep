import { beforeEach, describe, expect, it } from 'vitest'
import {
  exportProgress,
  getProgress,
  importProgress,
  recordAnswer,
  recordMockResult,
  reloadProgress,
  resetProgress,
  setLessonRead,
} from './store'

beforeEach(() => {
  localStorage.clear()
  resetProgress()
})

describe('progress store', () => {
  it('accumulates attempts per question and persists them', () => {
    recordAnswer('q-2.3-001', true, 1)
    recordAnswer('q-2.3-001', false, 2)
    reloadProgress()
    expect(getProgress().questions['q-2.3-001']).toEqual({
      attempts: 2,
      correct: 1,
      lastCorrect: false,
      lastAt: 2,
      streak: 0,
    })
  })

  it('counts consecutive correct answers and resets the streak on a wrong one', () => {
    for (const correct of [true, true, false, true, true, true]) recordAnswer('q-2.3-001', correct)
    expect(getProgress().questions['q-2.3-001']).toMatchObject({ attempts: 6, correct: 5, streak: 3 })
  })

  it('migrates version 1 data, estimating the streak from the last answer', () => {
    const v1 = { attempts: 3, correct: 2, lastAt: 5 }
    localStorage.setItem(
      'gridiron-prep:progress',
      JSON.stringify({
        version: 1,
        questions: { a: { ...v1, lastCorrect: true }, b: { ...v1, lastCorrect: false } },
        mockResults: [],
        lessonsRead: ['2.5'],
        labSteps: {},
      }),
    )
    reloadProgress()
    const progress = getProgress()
    expect(progress.version).toBe(2)
    expect(progress.questions.a.streak).toBe(1)
    expect(progress.questions.b.streak).toBe(0)
    expect(progress.lessonsRead).toEqual(['2.5'])
  })

  it('appends mock results', () => {
    recordMockResult({ at: 1, total: 10, correct: 8, scaledEstimate: 820, byDomain: [] })
    expect(getProgress().mockResults).toHaveLength(1)
  })

  it('discards stored data from an unknown version or corrupt JSON', () => {
    localStorage.setItem('gridiron-prep:progress', JSON.stringify({ version: 999, questions: { x: {} } }))
    reloadProgress()
    expect(getProgress().questions).toEqual({})
    localStorage.setItem('gridiron-prep:progress', '{not json')
    reloadProgress()
    expect(getProgress().questions).toEqual({})
  })

  it('round-trips progress through an export file', () => {
    recordAnswer('q-2.3-001', true, 5)
    setLessonRead('2.3', true)
    const file = exportProgress(new Date('2026-10-26T12:00:00Z'))
    expect(JSON.parse(file)).toMatchObject({ app: 'gridiron-prep', exportedAt: '2026-10-26T12:00:00.000Z' })
    const before = getProgress()
    resetProgress()
    importProgress(file)
    expect(getProgress()).toEqual(before)
    reloadProgress()
    expect(getProgress()).toEqual(before)
  })

  it('migrates a v1 export on import', () => {
    const v1 = { version: 1, questions: { 'q-1.1-001': { attempts: 1, correct: 1, lastCorrect: true, lastAt: 1 } } }
    importProgress(JSON.stringify({ app: 'gridiron-prep', progress: v1 }))
    expect(getProgress().questions['q-1.1-001'].streak).toBe(1)
  })

  it('rejects unusable files and keeps the current progress', () => {
    recordAnswer('q-2.3-001', true, 5)
    const before = getProgress()
    const exportOf = (progress: unknown) => JSON.stringify({ app: 'gridiron-prep', progress })
    expect(() => importProgress('{not json')).toThrow(/valid JSON/)
    expect(() => importProgress(JSON.stringify({ questions: {} }))).toThrow(/progress export/)
    expect(() => importProgress(exportOf({ version: 99 }))).toThrow(/newer version/)
    expect(() => importProgress(exportOf({ version: 2, questions: { x: { attempts: 'lots' } } }))).toThrow(/damaged/)
    expect(getProgress()).toBe(before)
  })
})

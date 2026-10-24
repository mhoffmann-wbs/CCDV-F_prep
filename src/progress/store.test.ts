import { beforeEach, describe, expect, it } from 'vitest'
import { getProgress, recordAnswer, recordMockResult, reloadProgress, resetProgress } from './store'

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
})

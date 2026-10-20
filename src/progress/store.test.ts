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
    })
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

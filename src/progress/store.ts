import { useSyncExternalStore } from 'react'
import type { DomainScore } from '../quiz/grading'

// All persisted learner state lives behind this module. Bump VERSION and add a
// migration in `load()` whenever the shape changes; never read localStorage elsewhere.
const STORAGE_KEY = 'gridiron-prep:progress'
const VERSION = 1

export interface QuestionStat {
  attempts: number
  correct: number
  lastCorrect: boolean
  lastAt: number
}

export interface MockResult {
  at: number
  total: number
  correct: number
  scaledEstimate: number
  byDomain: DomainScore[]
}

export interface Progress {
  version: typeof VERSION
  questions: Record<string, QuestionStat>
  mockResults: MockResult[]
}

function empty(): Progress {
  return { version: VERSION, questions: {}, mockResults: [] }
}

function load(): Progress {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return empty()
    const parsed = JSON.parse(raw) as Partial<Progress>
    if (parsed.version !== VERSION) return empty()
    return { ...empty(), ...parsed } as Progress
  } catch {
    return empty()
  }
}

let state: Progress = load()
const listeners = new Set<() => void>()

function commit(next: Progress) {
  state = next
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Storage can be unavailable (private mode, quota); keep in-memory state.
  }
  listeners.forEach((l) => l())
}

export function getProgress(): Progress {
  return state
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useProgress(): Progress {
  return useSyncExternalStore(subscribe, getProgress)
}

export function recordAnswer(questionId: string, correct: boolean, at: number = Date.now()) {
  const prev = state.questions[questionId] ?? { attempts: 0, correct: 0, lastCorrect: false, lastAt: 0 }
  commit({
    ...state,
    questions: {
      ...state.questions,
      [questionId]: {
        attempts: prev.attempts + 1,
        correct: prev.correct + (correct ? 1 : 0),
        lastCorrect: correct,
        lastAt: at,
      },
    },
  })
}

export function recordMockResult(result: MockResult) {
  commit({ ...state, mockResults: [...state.mockResults, result] })
}

export function resetProgress() {
  commit(empty())
}

/** Re-read from storage. Used by tests after manipulating localStorage directly. */
export function reloadProgress() {
  state = load()
  listeners.forEach((l) => l())
}

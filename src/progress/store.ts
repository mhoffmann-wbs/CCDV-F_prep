import { useSyncExternalStore } from 'react'
import { z } from 'zod'
import type { DomainScore } from '../quiz/grading'

// All persisted learner state lives behind this module. Bump VERSION and add a
// migration in `load()` whenever the shape changes; never read localStorage elsewhere.
const STORAGE_KEY = 'gridiron-prep:progress'
const VERSION = 2

export interface QuestionStat {
  attempts: number
  correct: number
  lastCorrect: boolean
  lastAt: number
  /** Consecutive correct answers; a wrong answer resets it to 0. */
  streak: number
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
  /** Skill ids whose lesson the learner marked as read. */
  lessonsRead: string[]
  /** Lab id -> ids of checklist steps the learner ticked. */
  labSteps: Record<string, string[]>
}

function empty(): Progress {
  return { version: VERSION, questions: {}, mockResults: [], lessonsRead: [], labSteps: {} }
}

function load(): Progress {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return empty()
    const parsed = JSON.parse(raw) as { version?: number; questions?: Record<string, Omit<QuestionStat, 'streak'>> }
    if (parsed.version === 1) return migrateV1(parsed)
    if (parsed.version !== VERSION) return empty()
    return { ...empty(), ...parsed } as Progress
  } catch {
    return empty()
  }
}

/** v1 had no streak. The best estimate from v1 data is 1 if the last answer was correct, else 0. */
function migrateV1(v1: { questions?: Record<string, Omit<QuestionStat, 'streak'>> }): Progress {
  const questions = Object.fromEntries(
    Object.entries(v1.questions ?? {}).map(([id, stat]) => [id, { ...stat, streak: stat.lastCorrect ? 1 : 0 }]),
  )
  return { ...empty(), ...v1, version: VERSION, questions }
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
  const prev = state.questions[questionId] ?? { attempts: 0, correct: 0, lastCorrect: false, lastAt: 0, streak: 0 }
  commit({
    ...state,
    questions: {
      ...state.questions,
      [questionId]: {
        attempts: prev.attempts + 1,
        correct: prev.correct + (correct ? 1 : 0),
        lastCorrect: correct,
        lastAt: at,
        streak: correct ? prev.streak + 1 : 0,
      },
    },
  })
}

export function recordMockResult(result: MockResult) {
  commit({ ...state, mockResults: [...state.mockResults, result] })
}

export function setLessonRead(skillId: string, read: boolean) {
  const others = state.lessonsRead.filter((id) => id !== skillId)
  commit({ ...state, lessonsRead: read ? [...others, skillId] : others })
}

export function setLabStep(labId: string, stepId: string, done: boolean) {
  const others = (state.labSteps[labId] ?? []).filter((id) => id !== stepId)
  commit({ ...state, labSteps: { ...state.labSteps, [labId]: done ? [...others, stepId] : others } })
}

// Imports come from files people pick, so they are validated in full before replacing anything.
const count = z.number().int().nonnegative()
const ProgressSchema = z.object({
  version: z.literal(VERSION),
  questions: z.record(
    z.string(),
    z.object({ attempts: count, correct: count, lastCorrect: z.boolean(), lastAt: z.number(), streak: count }),
  ),
  mockResults: z.array(
    z.object({
      at: z.number(),
      total: count,
      correct: count,
      scaledEstimate: z.number(),
      byDomain: z.array(z.object({ domainId: z.number(), title: z.string(), total: count, correct: count })),
    }),
  ),
  lessonsRead: z.array(z.string()),
  labSteps: z.record(z.string(), z.array(z.string())),
})

const EXPORT_APP = 'gridiron-prep'

/** The learner's progress as a JSON document they can save and import elsewhere. */
export function exportProgress(at: Date = new Date()): string {
  return JSON.stringify({ app: EXPORT_APP, exportedAt: at.toISOString(), progress: state }, null, 2)
}

/**
 * Replaces all progress with the contents of an export. Exports from the v1 store are migrated.
 * Throws an Error with a message for the learner if the file isn't a usable export.
 */
export function importProgress(json: string) {
  let doc: { app?: unknown; progress?: { version?: unknown } }
  try {
    doc = JSON.parse(json)
  } catch {
    throw new Error("This file isn't valid JSON.")
  }
  if (doc?.app !== EXPORT_APP || typeof doc.progress !== 'object' || doc.progress === null) {
    throw new Error("This file isn't a Gridiron Prep progress export.")
  }
  const { version } = doc.progress
  if (typeof version === 'number' && version > VERSION) {
    throw new Error('This export comes from a newer version of the app. Update the app, then import it again.')
  }
  // The schema check below catches anything the migration lets through.
  const raw = version === 1 ? migrateV1(doc.progress as Parameters<typeof migrateV1>[0]) : { ...empty(), ...doc.progress }
  const result = ProgressSchema.safeParse(raw)
  if (!result.success) throw new Error('This export is damaged or incomplete, so nothing was imported.')
  commit(result.data)
}

export function resetProgress() {
  commit(empty())
}

/** Re-read from storage. Used by tests after manipulating localStorage directly. */
export function reloadProgress() {
  state = load()
  listeners.forEach((l) => l())
}

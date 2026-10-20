import { EXAM_FORMAT, SKILLS, allocateItems } from '../content/blueprint'
import type { Question } from '../content/schema'

export type Rng = () => number

/** Deterministic PRNG (mulberry32) so tests can pin a seed. */
export function seededRng(seed: number): Rng {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export function shuffle<T>(items: readonly T[], rng: Rng = Math.random): T[] {
  const out = [...items]
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

export interface MockExam {
  questions: Question[]
  minutes: number
  /** How many items short of the real exam length the bank currently is. */
  shortfall: number
}

/**
 * Builds a mock exam weighted by the blueprint. Each skill contributes its allocated share;
 * if a skill's pool is too small, the gap is filled at random from the remaining bank.
 * Time is scaled to keep the real exam's pace (120 min / 53 items) when the bank is short.
 */
export function buildMockExam(bank: readonly Question[], rng: Rng = Math.random): MockExam {
  const allocation = allocateItems(EXAM_FORMAT.items)
  const picked: Question[] = []
  const leftover: Question[] = []
  for (const skill of SKILLS) {
    const pool = shuffle(
      bank.filter((q) => q.skillId === skill.id),
      rng,
    )
    const take = allocation.get(skill.id) ?? 0
    picked.push(...pool.slice(0, take))
    leftover.push(...pool.slice(take))
  }
  const missing = EXAM_FORMAT.items - picked.length
  picked.push(...shuffle(leftover, rng).slice(0, missing))

  const questions = shuffle(picked, rng)
  return {
    questions,
    minutes: Math.max(1, Math.round((EXAM_FORMAT.minutes * questions.length) / EXAM_FORMAT.items)),
    shortfall: EXAM_FORMAT.items - questions.length,
  }
}

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

/**
 * Draws an untimed mixed practice set across the whole blueprint. Unlike the mock exam's fixed
 * per-skill allocation (which, at small sizes, would only ever pick the heaviest skills), this
 * samples without replacement with each skill's chance proportional to its weight, so short sets
 * match the blueprint on average and every skill shows up over a few sessions.
 */
export function buildMixedSet(bank: readonly Question[], size: number, rng: Rng = Math.random): Question[] {
  const poolSize = new Map<string, number>()
  for (const q of bank) poolSize.set(q.skillId, (poolSize.get(q.skillId) ?? 0) + 1)
  const weight = new Map(SKILLS.map((s) => [s.id, s.weight]))
  // Efraimidis–Spirakis: key = u^(1/w); the largest keys form a weighted sample.
  const keyed = bank.map((q) => {
    const w = (weight.get(q.skillId) ?? 0) / (poolSize.get(q.skillId) ?? 1)
    return { q, key: w > 0 ? Math.pow(rng(), 1 / w) : -1 }
  })
  keyed.sort((a, b) => b.key - a.key)
  return shuffle(
    keyed.slice(0, size).map((k) => k.q),
    rng,
  )
}

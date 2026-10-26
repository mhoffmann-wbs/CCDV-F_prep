import { DOMAINS, SKILLS } from '../content/blueprint'
import type { Question } from '../content/schema'
import type { Progress, QuestionStat } from './store'

export interface SkillReadiness {
  skillId: string
  /** Share of the skill's questions answered at least once. */
  coverage: number
  /** Share of attempted questions whose latest answer was correct (0 if none attempted). */
  accuracy: number
  /** coverage × accuracy: what fraction of the skill's pool you can currently answer. */
  readiness: number
}

export function skillReadiness(bank: readonly Question[], progress: Progress): SkillReadiness[] {
  return SKILLS.map((skill) => {
    const pool = bank.filter((q) => q.skillId === skill.id)
    const attempted = pool.filter((q) => progress.questions[q.id])
    const correct = attempted.filter((q) => progress.questions[q.id].lastCorrect)
    const coverage = pool.length ? attempted.length / pool.length : 0
    const accuracy = attempted.length ? correct.length / attempted.length : 0
    return { skillId: skill.id, coverage, accuracy, readiness: coverage * accuracy }
  })
}

/** Domain and overall readiness, weighted by the blueprint's skill weights. */
export function weightedReadiness(skills: SkillReadiness[]) {
  const byId = new Map(skills.map((s) => [s.skillId, s]))
  const weighted = (ids: { id: string; weight: number }[]) => {
    const total = ids.reduce((sum, s) => sum + s.weight, 0)
    return ids.reduce((sum, s) => sum + (byId.get(s.id)?.readiness ?? 0) * s.weight, 0) / total
  }
  return {
    overall: weighted(SKILLS),
    domains: DOMAINS.map((d) => ({ domainId: d.id, title: d.title, readiness: weighted(d.skills) })),
  }
}

/**
 * Weak-area drill: questions from the lowest-readiness skills, preferring items
 * never attempted or last answered wrong. Heavier skills win ties.
 */
export function weakAreaQuestions(bank: readonly Question[], progress: Progress, skillCount = 5, size = 15): Question[] {
  const weight = new Map(SKILLS.map((s) => [s.id, s.weight]))
  const weakest = skillReadiness(bank, progress)
    .sort((a, b) => a.readiness - b.readiness || weight.get(b.skillId)! - weight.get(a.skillId)!)
    .slice(0, skillCount)
    .map((s) => s.skillId)
  return bank
    .filter((q) => weakest.includes(q.skillId) && !progress.questions[q.id]?.lastCorrect)
    .slice(0, size)
}

export type Mastery = 'untested' | 'recentError' | 'reviewed' | 'alwaysCorrect'

/** Display order: the levels that need attention first. */
export const MASTERY_LEVELS: { id: Mastery; label: string; tone: string }[] = [
  { id: 'recentError', label: 'Recent error', tone: 'border-red-600 bg-red-50' },
  { id: 'reviewed', label: 'Past error, since correct', tone: 'border-amber-300 bg-amber-50' },
  { id: 'untested', label: 'Not tested', tone: 'border-neutral-300 bg-neutral-100' },
  { id: 'alwaysCorrect', label: 'Always correct', tone: 'border-green-600 bg-green-50' },
]

/** One question's mastery, from its latest answer and whether it was ever missed. */
export function masteryOf(stat: QuestionStat | undefined): Mastery {
  if (!stat || stat.attempts === 0) return 'untested'
  if (!stat.lastCorrect) return 'recentError'
  return stat.correct < stat.attempts ? 'reviewed' : 'alwaysCorrect'
}

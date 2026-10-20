import { DOMAINS, EXAM_FORMAT, domainOf } from '../content/blueprint'
import type { Question } from '../content/schema'

/** Multiple-response items are all-or-nothing: the selected set must equal the key exactly. */
export function isCorrect(question: Question, selected: readonly string[]): boolean {
  if (selected.length !== question.correct.length) return false
  const key = new Set(question.correct)
  return selected.every((id) => key.has(id))
}

export interface DomainScore {
  domainId: number
  title: string
  total: number
  correct: number
}

export interface ScoreReport {
  total: number
  correct: number
  /** Estimated scaled score, 100–1,000. NOT the official scaling, which is not published. */
  scaledEstimate: number
  passed: boolean
  byDomain: DomainScore[]
}

/**
 * Linear raw-to-scaled estimate. The real exam is criterion-referenced with an unpublished
 * scale (Exam Guide §9), so the UI must always label this as an estimate.
 */
export function estimateScaled(fractionCorrect: number): number {
  const { scaledMin, scaledMax } = EXAM_FORMAT
  return Math.round(scaledMin + (scaledMax - scaledMin) * fractionCorrect)
}

export function scoreExam(
  questions: readonly Question[],
  answers: Readonly<Record<string, readonly string[]>>,
): ScoreReport {
  const byDomain = new Map<number, DomainScore>()
  let correct = 0
  for (const q of questions) {
    const domain = domainOf(q.skillId)!
    const entry = byDomain.get(domain.id) ?? {
      domainId: domain.id,
      title: domain.title,
      total: 0,
      correct: 0,
    }
    entry.total += 1
    if (isCorrect(q, answers[q.id] ?? [])) {
      entry.correct += 1
      correct += 1
    }
    byDomain.set(domain.id, entry)
  }
  const total = questions.length
  const scaledEstimate = estimateScaled(total === 0 ? 0 : correct / total)
  return {
    total,
    correct,
    scaledEstimate,
    passed: scaledEstimate >= EXAM_FORMAT.passingScaled,
    byDomain: DOMAINS.flatMap((d) => byDomain.get(d.id) ?? []),
  }
}

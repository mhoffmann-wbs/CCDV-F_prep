import type { Question } from './schema'

// Checks for the classic "test-wiseness" giveaways that make practice items easier than the
// real exam: a predictable answer letter, the key being the longest option, and repeated items.
// Used by content.test.ts (whole bank) and scripts/question-quality.ts (per file, for writers).

export const QUALITY_LIMITS = {
  /** No single letter may be the key in more than this share of single-select items. */
  maxLetterShare: 0.4,
  /** The key may be the strictly longest option in at most this share of single-select items. */
  maxLongestKeyShare: 0.4,
  /** Below this many single-select items, distribution limits are not meaningful. */
  minItemsForStats: 12,
} as const

export interface QualityReport {
  singleSelect: number
  multiSelect: number
  letterShare: Record<string, number>
  longestKeyShare: number
  duplicateStems: string[][]
  problems: string[]
}

function normalize(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}

export function analyzeQuestions(questions: readonly Question[]): QualityReport {
  // The Exam Guide's official samples keep their published option order.
  const original = questions.filter((q) => !q.official)
  const single = original.filter((q) => q.selectCount === 1)
  const letters: Record<string, number> = {}
  let longestKey = 0
  for (const q of single) {
    const key = q.correct[0]
    letters[key] = (letters[key] ?? 0) + 1
    const keyLength = q.options.find((o) => o.id === key)!.text.length
    if (q.options.every((o) => o.id === key || o.text.length < keyLength)) longestKey += 1
  }
  const letterShare = Object.fromEntries(
    Object.entries(letters).map(([letter, n]) => [letter, n / Math.max(1, single.length)]),
  )
  const longestKeyShare = longestKey / Math.max(1, single.length)

  const byStem = new Map<string, string[]>()
  for (const q of questions) {
    const k = normalize(q.stem)
    byStem.set(k, [...(byStem.get(k) ?? []), q.id])
  }
  const duplicateStems = [...byStem.values()].filter((ids) => ids.length > 1)

  const problems: string[] = []
  for (const ids of duplicateStems) problems.push(`duplicate stem: ${ids.join(', ')}`)
  for (const q of questions) {
    const texts = q.options.map((o) => normalize(o.text))
    if (new Set(texts).size !== texts.length) problems.push(`${q.id}: duplicate option text`)
  }
  if (single.length >= QUALITY_LIMITS.minItemsForStats) {
    for (const [letter, share] of Object.entries(letterShare)) {
      if (share > QUALITY_LIMITS.maxLetterShare) {
        problems.push(`key "${letter}" used in ${pct(share)} of single-select items (max ${pct(QUALITY_LIMITS.maxLetterShare)})`)
      }
    }
    if (longestKeyShare > QUALITY_LIMITS.maxLongestKeyShare) {
      problems.push(
        `key is the longest option in ${pct(longestKeyShare)} of single-select items (max ${pct(QUALITY_LIMITS.maxLongestKeyShare)})`,
      )
    }
  }

  return {
    singleSelect: single.length,
    multiSelect: original.length - single.length,
    letterShare,
    longestKeyShare,
    duplicateStems,
    problems,
  }
}

function pct(n: number): string {
  return `${Math.round(n * 100)}%`
}

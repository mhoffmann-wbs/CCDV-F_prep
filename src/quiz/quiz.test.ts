import { describe, expect, it } from 'vitest'
import { EXAM_FORMAT, SKILLS, allocateItems } from '../content/blueprint'
import type { Question } from '../content/schema'
import { estimateScaled, isCorrect, scoreExam } from './grading'
import { buildFocusSet, buildMixedSet, buildMockExam, orderLeastMastered, seededRng, shuffle } from './sampler'

function q(id: string, skillId: string, correct: string[] = ['A']): Question {
  return {
    id,
    skillId,
    difficulty: 1,
    stem: 'stem',
    selectCount: correct.length,
    options: ['A', 'B', 'C', 'D'].map((o) => ({ id: o, text: o, explanation: o })),
    correct,
    sourceLinks: ['https://example.com'],
  }
}

describe('isCorrect', () => {
  it('requires the exact set for multiple-response items', () => {
    const item = q('q-2.3-001', '2.3', ['A', 'C'])
    expect(isCorrect(item, ['C', 'A'])).toBe(true)
    expect(isCorrect(item, ['A'])).toBe(false)
    expect(isCorrect(item, ['A', 'B'])).toBe(false)
  })
})

describe('scoreExam', () => {
  it('reports per-domain results in blueprint order and an estimated scaled score', () => {
    const items = [q('q-8.1-001', '8.1'), q('q-2.3-001', '2.3'), q('q-2.3-002', '2.3')]
    const report = scoreExam(items, { 'q-2.3-001': ['A'], 'q-8.1-001': ['B'] })
    expect(report.correct).toBe(1)
    expect(report.byDomain.map((d) => [d.domainId, d.correct, d.total])).toEqual([
      [2, 1, 2],
      [8, 0, 1],
    ])
    expect(report.scaledEstimate).toBe(estimateScaled(1 / 3))
    expect(report.passed).toBe(false)
  })

  it('maps the scaled estimate onto 100–1,000', () => {
    expect(estimateScaled(0)).toBe(EXAM_FORMAT.scaledMin)
    expect(estimateScaled(1)).toBe(EXAM_FORMAT.scaledMax)
  })
})

describe('buildMockExam', () => {
  const fullBank = SKILLS.flatMap((s) =>
    Array.from({ length: 10 }, (_, i) => q(`q-${s.id}-${String(i).padStart(3, '0')}`, s.id)),
  )

  it('draws exactly the blueprint allocation per skill from a full bank', () => {
    const exam = buildMockExam(fullBank, seededRng(1))
    expect(exam.questions).toHaveLength(EXAM_FORMAT.items)
    expect(exam.minutes).toBe(EXAM_FORMAT.minutes)
    expect(exam.shortfall).toBe(0)
    for (const [skillId, n] of allocateItems()) {
      expect(exam.questions.filter((x) => x.skillId === skillId), skillId).toHaveLength(n)
    }
  })

  it('fills gaps from other skills and scales time when the bank is short', () => {
    const bank = Array.from({ length: 20 }, (_, i) => q(`q-2.3-${String(i).padStart(3, '0')}`, '2.3'))
    const exam = buildMockExam(bank, seededRng(2))
    expect(exam.questions).toHaveLength(20)
    expect(exam.shortfall).toBe(EXAM_FORMAT.items - 20)
    expect(exam.minutes).toBe(Math.round((120 * 20) / 53))
    expect(new Set(exam.questions.map((x) => x.id)).size).toBe(20)
  })
})

describe('buildMixedSet', () => {
  const bank = SKILLS.flatMap((s) =>
    Array.from({ length: 10 }, (_, i) => q(`q-${s.id}-${String(i).padStart(3, '0')}`, s.id)),
  )

  it('returns the requested number of distinct items, capped at the bank size', () => {
    const set = buildMixedSet(bank, 25, seededRng(4))
    expect(set).toHaveLength(25)
    expect(new Set(set.map((x) => x.id)).size).toBe(25)
    expect(buildMixedSet(bank.slice(0, 5), 25, seededRng(4))).toHaveLength(5)
  })

  it('favours heavier skills and still reaches light ones across sessions', () => {
    const counts = new Map<string, number>()
    for (let seed = 0; seed < 200; seed++) {
      for (const item of buildMixedSet(bank, 10, seededRng(seed))) {
        counts.set(item.skillId, (counts.get(item.skillId) ?? 0) + 1)
      }
    }
    const byWeight = [...SKILLS].sort((a, b) => a.weight - b.weight)
    const lightest = byWeight[0]
    const heaviest = byWeight[byWeight.length - 1]
    expect(counts.get(lightest.id) ?? 0).toBeGreaterThan(0)
    expect(counts.get(heaviest.id)!).toBeGreaterThan(counts.get(lightest.id)!)
    expect(counts.size).toBe(SKILLS.length)
  })
})

describe('buildFocusSet', () => {
  const bank = SKILLS.flatMap((s) =>
    Array.from({ length: 6 }, (_, i) => q(`q-${s.id}-${String(i).padStart(3, '0')}`, s.id)),
  )
  // Streaks run 0..5 within each skill, so each skill has exactly one question per streak.
  const streakOf = (id: string) => Number(id.slice(-3))
  const countBySkill = (items: Question[]) =>
    items.reduce((m, x) => m.set(x.skillId, (m.get(x.skillId) ?? 0) + 1), new Map<string, number>())

  it('keeps the same topic mix as a normal scrimmage', () => {
    for (let seed = 0; seed < 10; seed++) {
      const focus = buildFocusSet(bank, 25, streakOf, seededRng(seed))
      const mixed = buildMixedSet(bank, 25, seededRng(seed))
      expect(focus).toHaveLength(25)
      expect(countBySkill(focus)).toEqual(countBySkill(mixed))
    }
  })

  it('takes the lowest-streak questions within each topic', () => {
    for (let seed = 0; seed < 10; seed++) {
      const set = buildFocusSet(bank, 25, streakOf, seededRng(seed))
      for (const [skillId, count] of countBySkill(set)) {
        const streaks = set.filter((x) => x.skillId === skillId).map((x) => streakOf(x.id))
        expect(streaks.sort(), skillId).toEqual(Array.from({ length: count }, (_, i) => i))
      }
    }
  })
})

describe('orderLeastMastered', () => {
  it('keeps the whole pool, lowest streak first, shuffled within each streak', () => {
    const pool = Array.from({ length: 12 }, (_, i) => q(`q-2.3-${String(i).padStart(3, '0')}`, '2.3'))
    const streakOf = (id: string) => Number(id.slice(-3)) % 3
    const firsts = new Set<string>()
    for (let seed = 0; seed < 20; seed++) {
      const ordered = orderLeastMastered(pool, streakOf, seededRng(seed))
      expect(ordered).toHaveLength(12)
      expect(ordered.map((x) => streakOf(x.id))).toEqual([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2])
      firsts.add(ordered[0].id)
    }
    expect(firsts.size).toBeGreaterThan(1)
  })
})

describe('shuffle', () => {
  it('is a permutation and does not mutate the input', () => {
    const input = [1, 2, 3, 4, 5]
    const out = shuffle(input, seededRng(3))
    expect([...out].sort()).toEqual(input)
    expect(input).toEqual([1, 2, 3, 4, 5])
  })
})

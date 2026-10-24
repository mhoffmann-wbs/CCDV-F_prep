import { describe, expect, it } from 'vitest'
import { QUESTIONS } from '../content/questions'
import { skillReadiness, weakAreaQuestions, weightedReadiness } from './readiness'
import type { Progress } from './store'

const empty: Progress = { version: 2, questions: {}, mockResults: [], lessonsRead: [], labSteps: {} }

describe('readiness', () => {
  it('is zero with no progress and grows with correct answers', () => {
    expect(weightedReadiness(skillReadiness(QUESTIONS, empty)).overall).toBe(0)
    const pool = QUESTIONS.filter((q) => q.skillId === '2.5')
    const progress: Progress = {
      ...empty,
      questions: Object.fromEntries(pool.map((q) => [q.id, { attempts: 1, correct: 1, lastCorrect: true, lastAt: 1, streak: 1 }])),
    }
    const skills = skillReadiness(QUESTIONS, progress)
    expect(skills.find((s) => s.skillId === '2.5')!.readiness).toBe(1)
    expect(weightedReadiness(skills).overall).toBeCloseTo(0.086, 3)
  })

  it('drills the weakest skills and skips questions already answered correctly', () => {
    const drill = weakAreaQuestions(QUESTIONS, empty)
    expect(drill).toHaveLength(15)
    // With no progress, ties break toward the five heaviest skills.
    const heaviest = new Set(['2.5', '2.4', '2.3', '5.2', '1.2'])
    expect(drill.every((q) => heaviest.has(q.skillId))).toBe(true)
  })
})

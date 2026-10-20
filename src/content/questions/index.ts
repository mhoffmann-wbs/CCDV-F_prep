import { z } from 'zod'
import { QuestionSchema, type Question } from '../schema'

// One JSON file per domain: domain-<n>.json, each an array of questions.
const files = import.meta.glob<Question[]>('./domain-*.json', { eager: true, import: 'default' })

export const questionFiles: Record<string, unknown> = files

export const QUESTIONS: Question[] = Object.values(files).flatMap((raw) =>
  z.array(QuestionSchema).parse(raw),
)

export function questionsForSkill(skillId: string): Question[] {
  return QUESTIONS.filter((q) => q.skillId === skillId)
}

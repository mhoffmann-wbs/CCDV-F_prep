import { z } from 'zod'
import { QuestionSchema, type Question } from '../schema'

// One JSON file per blueprint skill: <skillId>.json (e.g. 2.3.json), each an array of questions.
const files = import.meta.glob<Question[]>('./*.json', { eager: true, import: 'default' })

export const questionFiles: Record<string, unknown> = files

export const QUESTIONS: Question[] = Object.values(files).flatMap((raw) =>
  z.array(QuestionSchema).parse(raw),
)

export function questionsForSkill(skillId: string): Question[] {
  return QUESTIONS.filter((q) => q.skillId === skillId)
}

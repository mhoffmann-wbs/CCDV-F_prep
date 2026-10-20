import { z } from 'zod'
import { getSkill } from './blueprint'

const OptionSchema = z.object({
  id: z.string().regex(/^[A-F]$/),
  text: z.string().min(1),
  /** Why this option is right or wrong. Required for every option, not just the key. */
  explanation: z.string().min(1),
})

export const QuestionSchema = z
  .object({
    id: z.string().regex(/^(q-\d\.\d-\d{3}|official-\d+)$/),
    skillId: z.string().refine((id) => getSkill(id) !== undefined, 'unknown skillId'),
    difficulty: z.union([z.literal(1), z.literal(2), z.literal(3)]),
    /** A realistic scenario ending in a question, in the style of Exam Guide §8. */
    stem: z.string().min(1),
    /** How many options to select. The exam states this on every item. */
    selectCount: z.number().int().min(1),
    options: z.array(OptionSchema).min(3).max(6),
    correct: z.array(z.string()).min(1),
    sourceLinks: z.array(z.url()).min(1),
    /** True only for the sample items published in the Exam Guide. */
    official: z.boolean().optional(),
  })
  .superRefine((q, ctx) => {
    const optionIds = q.options.map((o) => o.id)
    if (new Set(optionIds).size !== optionIds.length) {
      ctx.addIssue({ code: 'custom', message: 'duplicate option ids' })
    }
    if (q.correct.length !== q.selectCount) {
      ctx.addIssue({ code: 'custom', message: 'correct.length must equal selectCount' })
    }
    if (q.selectCount >= q.options.length) {
      ctx.addIssue({ code: 'custom', message: 'selectCount must be less than the number of options' })
    }
    for (const id of q.correct) {
      if (!optionIds.includes(id)) {
        ctx.addIssue({ code: 'custom', message: `correct id "${id}" is not an option` })
      }
    }
  })

export type Question = z.infer<typeof QuestionSchema>

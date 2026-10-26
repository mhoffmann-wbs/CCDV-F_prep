import { z } from 'zod'
import { LABS, getSkill, type LabId } from './blueprint'

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

/** `export const meta` of each lessons/<skillId>.mdx file. */
export const LessonMetaSchema = z.object({
  skillId: z.string().refine((id) => getSkill(id) !== undefined, 'unknown skillId'),
  /** Date the content was last checked against the official docs. */
  updated: z.iso.date(),
  tldr: z.string().min(1),
  /** Official documentation for this skill. Skilljar courses come from the blueprint. */
  links: z.array(z.object({ title: z.string().min(1), url: z.url() })).min(2),
})

export type LessonMeta = z.infer<typeof LessonMetaSchema>

/** `export const meta` of each labs/L<n>.mdx file. Lab titles and skills come from the blueprint. */
export const LabMetaSchema = z.object({
  labId: z.string().refine((id): id is LabId => id in LABS, 'unknown labId'),
  updated: z.iso.date(),
  minutes: z.number().int().positive(),
  goal: z.string().min(1),
  /** Folder under labs/ with starter.ts and solution.ts. */
  folder: z.string().regex(/^L\d+-[a-z0-9-]+$/),
  /** Checklist shown on the lab page; ids are stored in progress, so don't rename them. */
  steps: z
    .array(z.object({ id: z.string().regex(/^[a-z0-9-]+$/), title: z.string().min(1) }))
    .min(3),
})

export type LabMeta = z.infer<typeof LabMetaSchema>

/** `export const meta` of each guides/<slug>.mdx file (cheat sheet, exam-day strategy, ...). */
export const GuideMetaSchema = z.object({
  slug: z.string().regex(/^[a-z0-9-]+$/),
  /** Short label for the nav bar. */
  title: z.string().min(1),
  updated: z.iso.date(),
  summary: z.string().min(1),
})

export type GuideMeta = z.infer<typeof GuideMetaSchema>

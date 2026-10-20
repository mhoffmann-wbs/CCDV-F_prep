import type { ComponentType } from 'react'
import type { MDXComponents } from 'mdx/types'
import { LessonMetaSchema, type LessonMeta } from '../schema'

// One MDX file per blueprint skill: <skillId>.mdx (e.g. 2.5.mdx), exporting `meta`.
interface LessonModule {
  default: ComponentType<{ components?: MDXComponents }>
  meta: unknown
}

const modules = import.meta.glob<LessonModule>('./*.mdx', { eager: true })

export interface Lesson {
  meta: LessonMeta
  Content: LessonModule['default']
}

export const LESSONS: Map<string, Lesson> = new Map(
  Object.values(modules).map((mod) => {
    const meta = LessonMetaSchema.parse(mod.meta)
    return [meta.skillId, { meta, Content: mod.default }]
  }),
)

/** Every lesson body must contain these sections, in this order. */
export const REQUIRED_SECTIONS = ['## Key concepts', '## Exam traps', '## On the field'] as const

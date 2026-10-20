import type { ComponentType } from 'react'
import type { MDXComponents } from 'mdx/types'
import { LabMetaSchema, type LabMeta } from '../schema'

// One MDX file per lab: L<n>.mdx (e.g. L1.mdx), exporting `meta`.
interface LabModule {
  default: ComponentType<{ components?: MDXComponents }>
  meta: unknown
}

const modules = import.meta.glob<LabModule>('./*.mdx', { eager: true })

export interface Lab {
  meta: LabMeta
  Content: LabModule['default']
}

export const LAB_CONTENT: Map<string, Lab> = new Map(
  Object.values(modules).map((mod) => {
    const meta = LabMetaSchema.parse(mod.meta)
    return [meta.labId, { meta, Content: mod.default }]
  }),
)

/** Every lab body must contain these sections, in this order. */
export const REQUIRED_LAB_SECTIONS = ['## Why this lab', '## Setup', '## Steps', '## Done when', '## Exam angle'] as const

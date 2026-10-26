import type { ComponentType } from 'react'
import type { MDXComponents } from 'mdx/types'
import { GuideMetaSchema, type GuideMeta } from '../schema'

// One MDX file per study guide: <slug>.mdx (e.g. cheat-sheet.mdx), exporting `meta`.
interface GuideModule {
  default: ComponentType<{ components?: MDXComponents }>
  meta: unknown
}

const modules = import.meta.glob<GuideModule>('./*.mdx', { eager: true })

export interface Guide {
  meta: GuideMeta
  Content: GuideModule['default']
}

export const GUIDES: Map<string, Guide> = new Map(
  Object.values(modules).map((mod) => {
    const meta = GuideMetaSchema.parse(mod.meta)
    return [meta.slug, { meta, Content: mod.default }]
  }),
)

import type { ComponentProps } from 'react'
import { Link, useParams } from 'react-router'
import { GUIDES } from '../content/guides'

function ExternalLink(props: ComponentProps<'a'>) {
  const external = props.href?.startsWith('http')
  return <a {...props} {...(external ? { target: '_blank', rel: 'noreferrer' } : {})} />
}

export default function GuidePage() {
  const { slug } = useParams()
  const guide = slug ? GUIDES.get(slug) : undefined
  if (!guide) {
    return (
      <p>
        No such guide. <Link to="/" className="underline">Back to the playbook</Link>
      </p>
    )
  }
  const { meta, Content } = guide
  return (
    <article className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">{meta.title}</h1>
        <p className="text-neutral-600">{meta.summary}</p>
        <p className="flex items-center gap-3 text-sm text-neutral-500">
          Checked against the docs on {meta.updated}
          <button onClick={() => window.print()} className="rounded border px-3 py-1 print:hidden">
            Print
          </button>
        </p>
      </header>
      <div className="prose prose-neutral dark:prose-invert max-w-none prose-a:text-field-dark prose-code:before:content-none prose-code:after:content-none">
        <Content components={{ a: ExternalLink }} />
      </div>
    </article>
  )
}

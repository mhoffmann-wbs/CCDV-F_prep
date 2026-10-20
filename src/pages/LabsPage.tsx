import type { ComponentProps } from 'react'
import { Link, useParams } from 'react-router'
import { LABS, skillsForLab, type LabId } from '../content/blueprint'
import { LAB_CONTENT } from '../content/labs'
import { setLabStep, useProgress } from '../progress/store'

export default function LabsPage() {
  const { labId } = useParams()
  return labId ? <LabView labId={labId} /> : <LabIndex />
}

function LabIndex() {
  const { labSteps } = useProgress()
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Practice field</h1>
      <p className="text-neutral-600">
        Ten hands-on labs that together build one app, the <strong>Gridiron Assistant</strong>, on a fictional football
        league. You run them locally with your own API key; the code lives in the repo's <code>labs/</code> folder.
      </p>
      <ol className="space-y-3">
        {(Object.keys(LABS) as LabId[]).map((id) => {
          const lab = LAB_CONTENT.get(id)
          const done = labSteps[id]?.length ?? 0
          return (
            <li key={id} className="rounded-lg border border-neutral-200 bg-white p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                {lab ? (
                  <Link to={`/labs/${id}`} className="font-semibold text-field-dark hover:underline">
                    {id}: {LABS[id]}
                  </Link>
                ) : (
                  <span className="font-semibold text-neutral-400">
                    {id}: {LABS[id]} (coming soon)
                  </span>
                )}
                {lab && (
                  <span className="text-sm text-neutral-500">
                    {lab.meta.minutes} min · {done}/{lab.meta.steps.length} steps
                  </span>
                )}
              </div>
              {lab && <p className="mt-1 text-sm text-neutral-600">{lab.meta.goal}</p>}
              <p className="mt-2 text-xs text-neutral-500">
                Skills: {skillsForLab(id).map((s) => s.id).join(' · ')}
              </p>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function ExternalLink(props: ComponentProps<'a'>) {
  const external = props.href?.startsWith('http')
  return <a {...props} {...(external ? { target: '_blank', rel: 'noreferrer' } : {})} />
}

function LabView({ labId }: { labId: string }) {
  const { labSteps } = useProgress()
  const lab = LAB_CONTENT.get(labId)
  if (!lab) {
    return (
      <p>
        This lab isn't written yet. <Link to="/labs" className="underline">Back to the practice field</Link>
      </p>
    )
  }
  const { meta, Content } = lab
  const done = new Set(labSteps[labId] ?? [])

  return (
    <article className="space-y-6">
      <header className="space-y-2">
        <p className="text-sm text-neutral-500">
          <Link to="/labs" className="hover:underline">
            Practice field
          </Link>
        </p>
        <h1 className="text-3xl font-bold">
          {labId}: {LABS[labId as LabId]}
        </h1>
        <p className="text-neutral-700">{meta.goal}</p>
        <p className="text-sm text-neutral-600">
          About {meta.minutes} min · code in <code>labs/{meta.folder}/</code> · skills:{' '}
          {skillsForLab(labId as LabId).map((s, i) => (
            <span key={s.id}>
              {i > 0 && ', '}
              <Link to={`/learn/${s.id}`} className="text-field-dark underline">
                {s.id} {s.title}
              </Link>
            </span>
          ))}
        </p>
      </header>

      <section className="rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="font-semibold">
          Checklist ({done.size}/{meta.steps.length})
        </h2>
        <ul className="mt-2 space-y-1">
          {meta.steps.map((step) => (
            <li key={step.id}>
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={done.has(step.id)}
                  onChange={(e) => setLabStep(labId, step.id, e.target.checked)}
                  className="accent-field"
                />
                <span className={done.has(step.id) ? 'text-neutral-500 line-through' : ''}>{step.title}</span>
              </label>
            </li>
          ))}
        </ul>
      </section>

      <div className="prose prose-neutral dark:prose-invert max-w-none prose-a:text-field-dark prose-code:before:content-none prose-code:after:content-none">
        <Content components={{ a: ExternalLink }} />
      </div>
    </article>
  )
}

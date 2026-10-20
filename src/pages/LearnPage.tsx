import type { ComponentProps } from 'react'
import { Link, useParams } from 'react-router'
import { COURSES, DOMAINS, LABS, domainOf, getSkill } from '../content/blueprint'
import { LESSONS } from '../content/lessons'
import { questionsForSkill } from '../content/questions'
import { setLessonRead, useProgress } from '../progress/store'

export default function LearnPage() {
  const { skillId } = useParams()
  return skillId ? <LessonView skillId={skillId} /> : <LessonIndex />
}

function LessonIndex() {
  const { lessonsRead } = useProgress()
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Film room</h1>
      <p className="text-neutral-600">
        One lesson per blueprint skill. Each has a summary, the exam traps to watch for, an NFL example and
        links to the official material. {lessonsRead.length} of {LESSONS.size} marked as read.
      </p>
      {DOMAINS.map((domain) => (
        <section key={domain.id} className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="font-semibold">
            {domain.id}. {domain.title}
          </h2>
          <ul className="mt-2 space-y-1">
            {domain.skills.map((skill) => (
              <li key={skill.id} className="flex items-baseline gap-2 text-sm">
                <span className="w-4">{lessonsRead.includes(skill.id) ? '✓' : ''}</span>
                {LESSONS.has(skill.id) ? (
                  <Link to={`/learn/${skill.id}`} className="text-field-dark hover:underline">
                    {skill.id} {skill.title}
                  </Link>
                ) : (
                  <span className="text-neutral-400">
                    {skill.id} {skill.title} (coming soon)
                  </span>
                )}
                <span className="ml-auto font-mono text-xs text-neutral-500">{skill.weight}%</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

function ExternalLink(props: ComponentProps<'a'>) {
  const external = props.href?.startsWith('http')
  return <a {...props} {...(external ? { target: '_blank', rel: 'noreferrer' } : {})} />
}

function LessonView({ skillId }: { skillId: string }) {
  const { lessonsRead } = useProgress()
  const skill = getSkill(skillId)
  const lesson = LESSONS.get(skillId)
  if (!skill || !lesson) {
    return (
      <p>
        No lesson for this skill yet. <Link to="/learn" className="underline">Back to the film room</Link>
      </p>
    )
  }
  const { meta, Content } = lesson
  const read = lessonsRead.includes(skillId)
  const practiceCount = questionsForSkill(skillId).length

  return (
    <article className="space-y-6">
      <header className="space-y-2">
        <p className="text-sm text-neutral-500">
          <Link to="/learn" className="hover:underline">
            Film room
          </Link>{' '}
          / {domainOf(skillId)!.title}
        </p>
        <h1 className="text-3xl font-bold">
          {skill.id} {skill.title}
        </h1>
        <p className="text-sm text-neutral-600">
          {skill.weight}% of the exam · checked against the docs on {meta.updated}
        </p>
      </header>

      <p className="rounded-lg border-l-4 border-field bg-white p-4">
        <strong>TL;DR:</strong> {meta.tldr}
      </p>

      <div className="prose prose-neutral dark:prose-invert max-w-none prose-a:text-field-dark prose-code:before:content-none prose-code:after:content-none">
        <Content components={{ a: ExternalLink }} />
      </div>

      <section className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="font-semibold">Official docs</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {meta.links.map((link) => (
              <li key={link.url}>
                <ExternalLink href={link.url} className="text-field-dark underline">
                  {link.title}
                </ExternalLink>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="font-semibold">Official prep course</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {skill.courses.map((c) => (
              <li key={c}>
                <ExternalLink href={COURSES[c].url} className="text-field-dark underline">
                  {COURSES[c].title}
                </ExternalLink>{' '}
                <span className="text-neutral-500">({COURSES[c].minutes} min)</span>
              </li>
            ))}
          </ul>
          <h2 className="mt-4 font-semibold">Hands-on labs</h2>
          <ul className="mt-1 space-y-1 text-sm">
            {skill.labs.map((l) => (
              <li key={l}>
                <Link to={`/labs/${l}`} className="text-field-dark underline">
                  {l}: {LABS[l]}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <footer className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => setLessonRead(skillId, !read)}
          className={`rounded px-4 py-2 font-medium ${read ? 'border border-field text-field-dark' : 'bg-field text-chalk'}`}
        >
          {read ? '✓ Marked as read' : 'Mark as read'}
        </button>
        {practiceCount > 0 && (
          <Link to={`/practice?skill=${skillId}`} className="rounded border px-4 py-2">
            Practice this skill ({practiceCount})
          </Link>
        )}
      </footer>
    </article>
  )
}

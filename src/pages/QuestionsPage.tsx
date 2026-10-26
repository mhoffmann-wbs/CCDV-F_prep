import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { DOMAINS, SKILLS, getSkill } from '../content/blueprint'
import { QUESTIONS } from '../content/questions'
import type { Question } from '../content/schema'
import { MASTERY_LEVELS, masteryOf, type Mastery } from '../progress/readiness'
import { recordAnswer, useProgress, type Progress } from '../progress/store'
import QuestionView from '../quiz/QuestionView'
import { isCorrect } from '../quiz/grading'
import ShortcutHint from '../quiz/ShortcutHint'
import { useShortcuts } from '../quiz/shortcuts'

export default function QuestionsPage() {
  const { questionId } = useParams()
  // Keying on the id resets the answer state when moving to another question.
  return questionId ? <QuestionDetail key={questionId} questionId={questionId} /> : <QuestionIndex />
}

/** Questions matching the topic filter (`?skill=` or `?domain=`), in bank order. */
function topicPool(params: URLSearchParams): Question[] {
  const skillId = params.get('skill')
  const domainId = params.get('domain')
  if (skillId) return QUESTIONS.filter((q) => q.skillId === skillId)
  if (domainId) return QUESTIONS.filter((q) => q.skillId.startsWith(`${domainId}.`))
  return QUESTIONS
}

function filtered(params: URLSearchParams, progress: Progress): Question[] {
  const mastery = params.get('mastery')
  const pool = topicPool(params)
  return mastery ? pool.filter((q) => masteryOf(progress.questions[q.id]) === mastery) : pool
}

function MasteryBadge({ mastery }: { mastery: Mastery }) {
  const level = MASTERY_LEVELS.find((l) => l.id === mastery)!
  return <span className={`shrink-0 rounded border px-1.5 py-0.5 text-xs ${level.tone}`}>{level.label}</span>
}

function QuestionIndex() {
  const progress = useProgress()
  const [params, setParams] = useSearchParams()
  const pool = topicPool(params)
  const shown = filtered(params, progress)
  const mastery = params.get('mastery')
  const topic = params.get('skill') ? `skill=${params.get('skill')}` : params.get('domain') ? `domain=${params.get('domain')}` : ''

  function update(key: string, value: string | null) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  function setTopic(value: string) {
    const next = new URLSearchParams(params)
    next.delete('skill')
    next.delete('domain')
    if (value) {
      const [key, id] = value.split('=')
      next.set(key, id)
    }
    setParams(next, { replace: true })
  }

  const search = params.toString()
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Question bank</h1>
      <p className="text-neutral-600">
        Every question with your mastery of it. Open one to answer it on its own; the answer counts toward your
        progress like any practice rep.
      </p>

      <div className="space-y-3 rounded-lg border border-neutral-200 bg-white p-4">
        <label className="flex flex-wrap items-center gap-2 text-sm">
          Topic
          <select
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="max-w-full rounded border border-neutral-300 bg-white px-2 py-1"
          >
            <option value="">All topics ({QUESTIONS.length})</option>
            {DOMAINS.map((d) => (
              <optgroup key={d.id} label={`${d.id}. ${d.title}`}>
                <option value={`domain=${d.id}`}>
                  All of {d.id}. {d.title}
                </option>
                {d.skills.map((s) => (
                  <option key={s.id} value={`skill=${s.id}`}>
                    {s.id} {s.title}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Mastery filter">
          {MASTERY_LEVELS.map((level) => {
            const count = pool.filter((q) => masteryOf(progress.questions[q.id]) === level.id).length
            const active = mastery === level.id
            return (
              <button
                key={level.id}
                type="button"
                aria-pressed={active}
                onClick={() => update('mastery', active ? null : level.id)}
                className={`rounded border px-2 py-1 text-sm ${level.tone} ${active ? 'ring-2 ring-field' : ''}`}
              >
                {level.label} ({count})
              </button>
            )
          })}
        </div>
      </div>

      {shown.length === 0 && <p className="text-neutral-500">No questions match this filter.</p>}
      {SKILLS.map((skill) => {
        const items = shown.filter((q) => q.skillId === skill.id)
        if (items.length === 0) return null
        return (
          <section key={skill.id} className="rounded-lg border border-neutral-200 bg-white p-4">
            <h2 className="font-semibold">
              {skill.id} {skill.title}
            </h2>
            <ul className="mt-2 divide-y divide-neutral-100">
              {items.map((q) => (
                <li key={q.id}>
                  <Link
                    to={`/questions/${q.id}${search ? `?${search}` : ''}`}
                    className="flex items-start justify-between gap-3 py-2 text-sm hover:text-field-dark"
                  >
                    <span className="line-clamp-2">{q.stem}</span>
                    <MasteryBadge mastery={masteryOf(progress.questions[q.id])} />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

function QuestionDetail({ questionId }: { questionId: string }) {
  const progress = useProgress()
  const [params] = useSearchParams()
  const [selected, setSelected] = useState<string[]>([])
  const [revealed, setRevealed] = useState(false)
  const navigate = useNavigate()
  const question = QUESTIONS.find((q) => q.id === questionId)
  const search = params.toString() ? `?${params}` : ''

  // Prev/next walk the filtered list. Answering can move this question out of a mastery
  // filter, so it stays in the list for navigation.
  const list = filtered(params, progress)
  const nav =
    question && !list.some((q) => q.id === question.id)
      ? QUESTIONS.filter((q) => q.id === question.id || list.includes(q))
      : list
  const index = question ? nav.findIndex((q) => q.id === question.id) : -1
  const prev = index > 0 ? nav[index - 1] : undefined
  const next = index >= 0 ? nav[index + 1] : undefined

  // Declared before the early return below, so the handlers guard against a missing question.
  useShortcuts({
    Enter: () => {
      if (question && !revealed && selected.length === question.selectCount) check()
    },
    ArrowLeft: () => prev && navigate(`/questions/${prev.id}${search}`),
    ArrowRight: () => next && navigate(`/questions/${next.id}${search}`),
  })

  if (!question) {
    return (
      <p>
        No such question. <Link to="/questions" className="underline">Back to the question bank</Link>
      </p>
    )
  }

  function check() {
    recordAnswer(question!.id, isCorrect(question!, selected))
    setRevealed(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 text-sm text-neutral-600">
        <Link to={`/questions${search}`} className="hover:underline">
          ← Question bank
        </Link>
        <span className="flex items-center gap-2">
          {index + 1} of {nav.length} · <MasteryBadge mastery={masteryOf(progress.questions[question.id])} />
        </span>
      </div>
      <QuestionView question={question} selected={selected} onChange={setSelected} revealed={revealed} keyboard />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-3 text-sm">
          {prev && (
            <Link to={`/questions/${prev.id}${search}`} className="rounded border px-3 py-2">
              ← Previous
            </Link>
          )}
          {next && (
            <Link to={`/questions/${next.id}${search}`} className="rounded border px-3 py-2">
              Next →
            </Link>
          )}
        </div>
        {!revealed && (
          <button
            onClick={check}
            disabled={selected.length !== question.selectCount}
            className="rounded bg-field px-4 py-2 font-medium text-chalk disabled:opacity-40"
          >
            Check answer
          </button>
        )}
      </div>
      <ShortcutHint items={[['1–6', 'or A–F select'], ['Enter', 'check'], ['← →', 'previous / next']]} />
      <p className="text-xs text-neutral-500">
        Lesson:{' '}
        <Link to={`/learn/${question.skillId}`} className="underline">
          {question.skillId} {getSkill(question.skillId)!.title}
        </Link>
      </p>
    </div>
  )
}

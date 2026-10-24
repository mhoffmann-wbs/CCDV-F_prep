import { useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router'
import { DOMAINS, EXAM_FORMAT, getSkill } from '../content/blueprint'
import { QUESTIONS } from '../content/questions'
import { weakAreaQuestions } from '../progress/readiness'
import { getProgress, recordAnswer } from '../progress/store'
import QuestionView from '../quiz/QuestionView'
import { isCorrect, scoreExam } from '../quiz/grading'
import { DomainTable } from '../quiz/ScoreReportView'
import { buildMixedSet, shuffle } from '../quiz/sampler'

/** Sizes offered for a mixed scrimmage; the last one matches the real exam length. */
const MIX_SIZES = [10, 25, EXAM_FORMAT.items]

export default function PracticePage() {
  const [params] = useSearchParams()
  const skillId = params.get('skill')
  const domainId = params.get('domain')
  const mix = Number(params.get('mix'))

  if (params.get('weak')) {
    // Snapshot progress once so answering during the drill doesn't reshuffle it.
    return <PracticeSession key="weak" pool={weakAreaQuestions(QUESTIONS, getProgress())} label="Weak-area drill" />
  }
  if (mix > 0) {
    return <PracticeSession key={`mix|${mix}`} pool={buildMixedSet(QUESTIONS, mix)} label="Mixed scrimmage" />
  }
  if (!skillId && !domainId) return <PracticePicker />

  const pool = QUESTIONS.filter((q) =>
    skillId ? q.skillId === skillId : q.skillId.startsWith(`${domainId}.`),
  )
  const label = skillId
    ? `${skillId} ${getSkill(skillId)?.title ?? ''}`
    : DOMAINS.find((d) => String(d.id) === domainId)?.title
  // Keying on the selection resets the session when the user picks something else.
  return <PracticeSession key={`${skillId}|${domainId}`} pool={pool} label={label ?? ''} />
}

function PracticePicker() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Practice reps</h1>
      <p className="text-neutral-600">
        Pick a domain or a single skill, or run a mixed scrimmage across the whole blueprint. You get
        immediate feedback, with an explanation for every option.
      </p>
      <section className="rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="font-semibold">Mixed scrimmage</h2>
        <p className="mt-1 text-sm text-neutral-600">
          Questions from every domain, drawn by blueprint weight like the mock exam, but untimed and with the
          answer revealed after each item.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {MIX_SIZES.map((n) => (
            <Link
              key={n}
              to={`?mix=${n}`}
              className="rounded border border-field px-3 py-1 text-sm text-field-dark hover:bg-field/10"
            >
              {n} questions
            </Link>
          ))}
        </div>
      </section>
      {DOMAINS.map((domain) => {
        const domainCount = QUESTIONS.filter((q) => q.skillId.startsWith(`${domain.id}.`)).length
        return (
          <section key={domain.id} className="rounded-lg border border-neutral-200 bg-white p-4">
            <h2 className="flex items-baseline justify-between font-semibold">
              <PracticeLink to={`?domain=${domain.id}`} count={domainCount}>
                {domain.id}. {domain.title}
              </PracticeLink>
            </h2>
            <ul className="mt-2 grid gap-1 sm:grid-cols-2">
              {domain.skills.map((skill) => (
                <li key={skill.id} className="text-sm">
                  <PracticeLink
                    to={`?skill=${skill.id}`}
                    count={QUESTIONS.filter((q) => q.skillId === skill.id).length}
                  >
                    {skill.id} {skill.title}
                  </PracticeLink>
                </li>
              ))}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

function PracticeLink({ to, count, children }: { to: string; count: number; children: ReactNode }) {
  if (count === 0) {
    return (
      <span className="text-neutral-400">
        {children} <span className="text-xs">(no questions yet)</span>
      </span>
    )
  }
  return (
    <Link to={to} className="text-field-dark underline-offset-2 hover:underline">
      {children} <span className="text-xs text-neutral-500">({count})</span>
    </Link>
  )
}

function PracticeSession({ pool, label }: { pool: typeof QUESTIONS; label: string }) {
  const [questions] = useState(() => shuffle(pool))
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<string[]>([])
  const [revealed, setRevealed] = useState(false)
  const [answers, setAnswers] = useState<Record<string, string[]>>({})

  if (questions.length === 0) {
    return <p>No questions for this selection yet.</p>
  }

  const answered = questions.filter((q) => q.id in answers)
  const score = scoreExam(answered, answers)

  const done = index >= questions.length
  if (done) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Drive complete: {label}</h1>
        <p>
          {score.correct} / {score.total} correct.
        </p>
        {/* A single-skill or single-domain drill would just repeat the total. */}
        {score.byDomain.length > 1 && <DomainTable byDomain={score.byDomain} />}
        <Link to="/practice" className="underline">
          Back to practice
        </Link>
      </div>
    )
  }

  const question = questions[index]

  function check() {
    const correct = isCorrect(question, selected)
    recordAnswer(question.id, correct)
    setAnswers((a) => ({ ...a, [question.id]: selected }))
    setRevealed(true)
  }

  function next() {
    setIndex((i) => i + 1)
    setSelected([])
    setRevealed(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 text-sm text-neutral-600">
        <span>{label}</span>
        <span>
          Question {index + 1} of {questions.length} · {score.correct}/{score.total} correct
        </span>
      </div>
      <QuestionView question={question} selected={selected} onChange={setSelected} revealed={revealed} />
      <div className="flex justify-end">
        {revealed ? (
          <button onClick={next} className="rounded bg-field px-4 py-2 font-medium text-chalk">
            {index + 1 === questions.length ? 'Finish' : 'Next play'}
          </button>
        ) : (
          <button
            onClick={check}
            disabled={selected.length !== question.selectCount}
            className="rounded bg-field px-4 py-2 font-medium text-chalk disabled:opacity-40"
          >
            Check answer
          </button>
        )}
      </div>
    </div>
  )
}

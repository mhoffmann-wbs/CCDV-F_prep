import { useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router'
import { DOMAINS, EXAM_FORMAT, getSkill } from '../content/blueprint'
import { QUESTIONS } from '../content/questions'
import { weakAreaQuestions } from '../progress/readiness'
import { getProgress, recordAnswer } from '../progress/store'
import QuestionView from '../quiz/QuestionView'
import { isCorrect, scoreExam } from '../quiz/grading'
import { DomainTable } from '../quiz/ScoreReportView'
import { buildFocusSet, buildMixedSet, orderLeastMastered, shuffle } from '../quiz/sampler'

/** Sizes offered for a mixed scrimmage; the last one matches the real exam length. */
const MIX_SIZES = [10, 25, EXAM_FORMAT.items]

const MODES = [
  { focus: false, label: 'Any question', hint: 'Random order. Scrimmages are weighted by the blueprint.' },
  {
    focus: true,
    label: 'Least mastered',
    hint: 'Within each topic, questions with the shortest run of correct answers come first (a wrong answer resets the run), in random order among equals. Scrimmages keep the blueprint mix of topics.',
  },
]

export default function PracticePage() {
  const [params] = useSearchParams()
  const skillId = params.get('skill')
  const domainId = params.get('domain')
  const mix = Number(params.get('mix'))
  const focus = params.get('focus') === '1'
  // Progress is read once per selection (sessions keep their first order), so answering
  // during a session doesn't reshuffle it.
  const { questions: stats } = getProgress()
  const streakOf = (id: string) => stats[id]?.streak ?? 0
  const suffix = focus ? ': least mastered' : ''

  if (params.get('weak')) {
    return <PracticeSession key="weak" questions={shuffle(weakAreaQuestions(QUESTIONS, getProgress()))} label="Weak-area drill" />
  }
  if (mix > 0) {
    const questions = focus ? buildFocusSet(QUESTIONS, mix, streakOf) : buildMixedSet(QUESTIONS, mix)
    return <PracticeSession key={`mix|${mix}|${focus}`} questions={questions} label={`Mixed scrimmage${suffix}`} />
  }
  if (!skillId && !domainId) return <PracticePicker />

  const pool = QUESTIONS.filter((q) =>
    skillId ? q.skillId === skillId : q.skillId.startsWith(`${domainId}.`),
  )
  const label = skillId
    ? `${skillId} ${getSkill(skillId)?.title ?? ''}`
    : DOMAINS.find((d) => String(d.id) === domainId)?.title
  // Keying on the selection resets the session when the user picks something else.
  return (
    <PracticeSession
      key={`${skillId}|${domainId}|${focus}`}
      questions={focus ? orderLeastMastered(pool, streakOf) : shuffle(pool)}
      label={`${label ?? ''}${suffix}`}
    />
  )
}

function PracticePicker() {
  const [focus, setFocus] = useState(false)
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Practice reps</h1>
      <p className="text-neutral-600">
        Pick a domain or a single skill, or run a mixed scrimmage across the whole blueprint. You get
        immediate feedback, with an explanation for every option.
      </p>
      <div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Question selection">
          {MODES.map((mode) => (
            <button
              key={mode.label}
              type="button"
              aria-pressed={focus === mode.focus}
              onClick={() => setFocus(mode.focus)}
              className={`rounded px-3 py-1 text-sm ${
                focus === mode.focus ? 'bg-field text-chalk' : 'border border-neutral-300 text-neutral-700'
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-neutral-500">{MODES.find((m) => m.focus === focus)!.hint}</p>
      </div>
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
              to={withMode(`?mix=${n}`, focus)}
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
              <PracticeLink to={withMode(`?domain=${domain.id}`, focus)} count={domainCount}>
                {domain.id}. {domain.title}
              </PracticeLink>
            </h2>
            <ul className="mt-2 grid gap-1 sm:grid-cols-2">
              {domain.skills.map((skill) => (
                <li key={skill.id} className="text-sm">
                  <PracticeLink
                    to={withMode(`?skill=${skill.id}`, focus)}
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

function withMode(search: string, focus: boolean) {
  return focus ? `${search}&focus=1` : search
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

/** Runs `questions` in the order given; callers decide how they are sampled and ordered. */
function PracticeSession({ questions: initial, label }: { questions: typeof QUESTIONS; label: string }) {
  const [questions] = useState(initial)
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

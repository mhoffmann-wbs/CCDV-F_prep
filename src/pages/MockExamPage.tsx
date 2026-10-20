import { useCallback, useEffect, useState } from 'react'
import { EXAM_FORMAT } from '../content/blueprint'
import { QUESTIONS } from '../content/questions'
import { recordAnswer, recordMockResult } from '../progress/store'
import QuestionView from '../quiz/QuestionView'
import ScoreReportView from '../quiz/ScoreReportView'
import { isCorrect, scoreExam, type ScoreReport } from '../quiz/grading'
import { buildMockExam, type MockExam } from '../quiz/sampler'

type Answers = Record<string, string[]>

export default function MockExamPage() {
  const [exam, setExam] = useState<MockExam | null>(null)
  const [result, setResult] = useState<{ report: ScoreReport; answers: Answers } | null>(null)

  if (result && exam) {
    return (
      <MockResults
        exam={exam}
        report={result.report}
        answers={result.answers}
        onRestart={() => {
          setExam(null)
          setResult(null)
        }}
      />
    )
  }
  if (exam) {
    return (
      <MockRunner
        exam={exam}
        onSubmit={(answers) => {
          const report = scoreExam(exam.questions, answers)
          const at = Date.now()
          for (const q of exam.questions) recordAnswer(q.id, isCorrect(q, answers[q.id] ?? []), at)
          recordMockResult({ at, ...report })
          setResult({ report, answers })
        }}
      />
    )
  }
  return <MockIntro onStart={() => setExam(buildMockExam(QUESTIONS))} />
}

function MockIntro({ onStart }: { onStart: () => void }) {
  const preview = buildMockExam(QUESTIONS)
  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-3xl font-bold">Mock exam: game day</h1>
      <p>
        The real CCDV-F has {EXAM_FORMAT.items} items in {EXAM_FORMAT.minutes} minutes. Items are drawn by
        blueprint weight. There is no feedback until you submit, and you can flag items and review them before
        submitting.
      </p>
      {preview.shortfall > 0 && (
        <p className="rounded border border-amber-300 bg-amber-50 p-3 text-sm">
          The question bank is still growing. This mock has <strong>{preview.questions.length}</strong> items,
          and its time limit is scaled to the real exam's pace: <strong>{preview.minutes} min</strong>.
        </p>
      )}
      <button onClick={onStart} className="rounded bg-field px-5 py-2 font-medium text-chalk">
        Kick off
      </button>
    </div>
  )
}

function MockRunner({ exam, onSubmit }: { exam: MockExam; onSubmit: (answers: Answers) => void }) {
  const [deadline] = useState(() => Date.now() + exam.minutes * 60_000)
  const [now, setNow] = useState(() => Date.now())
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState<Answers>({})
  const [flagged, setFlagged] = useState<Set<string>>(new Set())
  const [reviewing, setReviewing] = useState(false)

  const submit = useCallback(() => onSubmit(answers), [answers, onSubmit])
  const remaining = Math.max(0, deadline - now)

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (remaining === 0) submit()
  }, [remaining, submit])

  const question = exam.questions[index]
  const isAnswered = (id: string, selectCount: number) => (answers[id]?.length ?? 0) === selectCount
  const unanswered = exam.questions.filter((q) => !isAnswered(q.id, q.selectCount)).length

  function toggleFlag(id: string) {
    setFlagged((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="space-y-6">
      <div className="sticky top-0 z-10 flex items-center justify-between rounded bg-field-dark px-4 py-2 text-chalk">
        <span>
          {reviewing ? 'Review' : `Item ${index + 1} of ${exam.questions.length}`}
        </span>
        <span className="font-mono" aria-label="time remaining">
          {formatClock(remaining)}
        </span>
      </div>

      {reviewing ? (
        <div className="space-y-4">
          <p>
            {unanswered === 0 ? 'All items answered.' : `${unanswered} item(s) unanswered.`} {flagged.size}{' '}
            flagged.
          </p>
          <ol className="grid grid-cols-6 gap-2 sm:grid-cols-10">
            {exam.questions.map((q, i) => (
              <li key={q.id}>
                <button
                  onClick={() => {
                    setIndex(i)
                    setReviewing(false)
                  }}
                  className={`w-full rounded border px-2 py-1 text-sm ${
                    isAnswered(q.id, q.selectCount) ? 'border-field bg-field/10' : 'border-neutral-300 bg-white'
                  } ${flagged.has(q.id) ? 'ring-2 ring-amber-400' : ''}`}
                >
                  {i + 1}
                  {flagged.has(q.id) ? ' ⚑' : ''}
                </button>
              </li>
            ))}
          </ol>
          <div className="flex justify-between">
            <button onClick={() => setReviewing(false)} className="rounded border px-4 py-2">
              Back to items
            </button>
            <button onClick={submit} className="rounded bg-pigskin px-4 py-2 font-medium text-chalk">
              Submit exam
            </button>
          </div>
        </div>
      ) : (
        <>
          <QuestionView
            question={question}
            selected={answers[question.id] ?? []}
            onChange={(sel) => setAnswers((a) => ({ ...a, [question.id]: sel }))}
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <button
              onClick={() => setIndex((i) => i - 1)}
              disabled={index === 0}
              className="rounded border px-4 py-2 disabled:opacity-40"
            >
              Previous
            </button>
            <button onClick={() => toggleFlag(question.id)} className="rounded border px-4 py-2">
              {flagged.has(question.id) ? 'Unflag' : 'Flag for review'}
            </button>
            {index + 1 < exam.questions.length ? (
              <button onClick={() => setIndex((i) => i + 1)} className="rounded bg-field px-4 py-2 text-chalk">
                Next
              </button>
            ) : (
              <button onClick={() => setReviewing(true)} className="rounded bg-field px-4 py-2 text-chalk">
                Review
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function MockResults({
  exam,
  report,
  answers,
  onRestart,
}: {
  exam: MockExam
  report: ScoreReport
  answers: Answers
  onRestart: () => void
}) {
  const [showReview, setShowReview] = useState(false)
  return (
    <div className="space-y-8">
      <ScoreReportView report={report} />
      <div className="flex gap-3">
        <button onClick={() => setShowReview((v) => !v)} className="rounded border px-4 py-2">
          {showReview ? 'Hide answers' : 'Review answers'}
        </button>
        <button onClick={onRestart} className="rounded bg-field px-4 py-2 text-chalk">
          New mock exam
        </button>
      </div>
      {showReview &&
        exam.questions.map((q, i) => (
          <section key={q.id} className="border-t border-neutral-200 pt-6">
            <p className="mb-2 text-sm text-neutral-500">Item {i + 1}</p>
            <QuestionView question={q} selected={answers[q.id] ?? []} onChange={() => {}} revealed />
          </section>
        ))}
    </div>
  )
}

function formatClock(ms: number): string {
  const total = Math.ceil(ms / 1000)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

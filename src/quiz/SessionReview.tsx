import { Link } from 'react-router'
import type { Question } from '../content/schema'
import QuestionView from './QuestionView'
import { isCorrect } from './grading'

/**
 * End-of-session review: every answered question, misses first, each expandable to the
 * full item with the learner's answer and all explanations.
 */
export default function SessionReview({
  questions,
  answers,
}: {
  questions: readonly Question[]
  answers: Record<string, string[]>
}) {
  const answered = questions.filter((q) => q.id in answers)
  const missed = answered.filter((q) => !isCorrect(q, answers[q.id]))
  const right = answered.filter((q) => isCorrect(q, answers[q.id]))

  return (
    <section className="space-y-2">
      <h2 className="text-xl font-semibold">Film review</h2>
      <p className="text-sm text-neutral-600">
        {missed.length > 0 ? 'Misses first. ' : ''}Open a question to see your answer and every explanation.
      </p>
      <ul className="space-y-2">
        {[...missed, ...right].map((q) => {
          const correct = isCorrect(q, answers[q.id])
          return (
            <li key={q.id}>
              <details
                className={`rounded-lg border-l-4 bg-white p-3 ${correct ? 'border-green-600' : 'border-red-600'}`}
              >
                <summary className="flex cursor-pointer gap-2">
                  <span aria-label={correct ? 'correct' : 'missed'}>{correct ? '✓' : '✗'}</span>
                  <span className="line-clamp-2">{q.stem}</span>
                </summary>
                <div className="mt-4 space-y-3">
                  <QuestionView question={q} selected={answers[q.id]} onChange={() => {}} revealed />
                  <Link to={`/questions/${q.id}`} className="text-sm text-field-dark underline">
                    Try this question again
                  </Link>
                </div>
              </details>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

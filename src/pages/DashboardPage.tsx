import { Link } from 'react-router'
import { EXAM_FORMAT, LABS, SKILLS, getSkill } from '../content/blueprint'
import { QUESTIONS } from '../content/questions'
import { skillReadiness, weightedReadiness } from '../progress/readiness'
import { useProgress } from '../progress/store'

const pct = (n: number) => `${Math.round(n * 100)}%`

export default function DashboardPage() {
  const progress = useProgress()
  const skills = skillReadiness(QUESTIONS, progress)
  const { overall, domains } = weightedReadiness(skills)
  const weakest = [...skills].sort((a, b) => a.readiness - b.readiness).slice(0, 5)
  const lastMock = progress.mockResults.at(-1)
  const labsStarted = Object.values(progress.labSteps).filter((s) => s.length > 0).length

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <h1 className="text-3xl font-bold">Scoreboard</h1>
        <p className="text-neutral-600">
          Readiness is the share of each skill's question pool you can currently answer, weighted by the exam
          blueprint. It's a study guide, not a score prediction.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-4">
        <Stat label="Weighted readiness" value={pct(overall)} />
        <Stat
          label="Last mock (estimated)"
          value={lastMock ? String(lastMock.scaledEstimate) : '–'}
          hint={`pass at ${EXAM_FORMAT.passingScaled}`}
        />
        <Stat label="Lessons read" value={`${progress.lessonsRead.length}/${SKILLS.length}`} />
        <Stat label="Labs started" value={`${labsStarted}/${Object.keys(LABS).length}`} />
      </section>

      <section className="rounded-lg border border-neutral-200 bg-white p-4">
        <h2 className="font-semibold">By domain</h2>
        <ul className="mt-3 space-y-2">
          {domains.map((d) => (
            <li key={d.domainId}>
              <div className="flex justify-between text-sm">
                <span>
                  {d.domainId}. {d.title}
                </span>
                <span className="font-mono">{pct(d.readiness)}</span>
              </div>
              <div className="mt-1 h-2 rounded bg-neutral-100" role="presentation">
                <div className="h-2 rounded bg-field" style={{ width: pct(d.readiness) }} />
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-neutral-200 bg-white p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-semibold">Weakest skills</h2>
          <Link to="/practice?weak=1" className="rounded bg-pigskin px-4 py-2 text-sm font-medium text-chalk">
            Run the weak-area drill
          </Link>
        </div>
        <ul className="mt-3 space-y-1 text-sm">
          {weakest.map((s) => (
            <li key={s.skillId} className="flex justify-between gap-4">
              <Link to={`/learn/${s.skillId}`} className="text-field-dark hover:underline">
                {s.skillId} {getSkill(s.skillId)!.title}
              </Link>
              <span className="text-neutral-500">
                {pct(s.coverage)} seen · {pct(s.accuracy)} right
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-neutral-500">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {hint && <p className="text-xs text-neutral-500">{hint}</p>}
    </div>
  )
}

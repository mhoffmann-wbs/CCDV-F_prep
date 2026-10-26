import { useState, type ChangeEvent } from 'react'
import { Link } from 'react-router'
import { EXAM_FORMAT, LABS, SKILLS, getSkill } from '../content/blueprint'
import { QUESTIONS } from '../content/questions'
import { skillReadiness, weightedReadiness } from '../progress/readiness'
import { exportProgress, importProgress, useProgress } from '../progress/store'

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

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
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

      <YourData />
    </div>
  )
}

/** Progress lives in this browser only, so learners can move it between devices as a file. */
function YourData() {
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  function download() {
    const url = URL.createObjectURL(new Blob([exportProgress()], { type: 'application/json' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `gridiron-prep-progress-${new Date().toISOString().slice(0, 10)}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = '' // let the same file be picked again
    if (!file) return
    if (!window.confirm('Importing replaces all progress in this browser. Continue?')) return
    try {
      importProgress(await file.text())
      setMessage({ ok: true, text: `Imported progress from ${file.name}.` })
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message })
    }
  }

  return (
    <section className="rounded-lg border border-neutral-200 bg-white p-4">
      <h2 className="font-semibold">Your data</h2>
      <p className="mt-1 text-sm text-neutral-600">
        Progress is saved in this browser only. Export it to keep a backup or to continue on another device, then
        import the file there.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button onClick={download} className="rounded border px-4 py-2 text-sm">
          Export progress
        </button>
        <label className="cursor-pointer rounded border px-4 py-2 text-sm">
          Import progress
          <input type="file" accept="application/json,.json" onChange={upload} className="sr-only" />
        </label>
      </div>
      {message && (
        <p role="status" className={`mt-2 text-sm ${message.ok ? 'text-green-600' : 'text-red-600'}`}>
          {message.text}
        </p>
      )}
    </section>
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

import {
  COURSES,
  DOMAINS,
  EXAM_FORMAT,
  EXAM_GUIDE,
  LABS,
  SKILLJAR_PATH_URL,
  domainWeight,
} from '../content/blueprint'
import { questionsForSkill } from '../content/questions'

export default function BlueprintPage() {
  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-3xl font-bold">The playbook: CCDV-F blueprint</h1>
        <p className="mt-2 text-neutral-600">
          {EXAM_FORMAT.items} items · {EXAM_FORMAT.minutes} minutes · pass at {EXAM_FORMAT.passingScaled}{' '}
          on a {EXAM_FORMAT.scaledMin}–{EXAM_FORMAT.scaledMax} scale. Source:{' '}
          <a className="underline" href={EXAM_GUIDE.url} target="_blank" rel="noreferrer">
            Exam Guide v{EXAM_GUIDE.version}
          </a>{' '}
          and the{' '}
          <a className="underline" href={SKILLJAR_PATH_URL} target="_blank" rel="noreferrer">
            official prep path
          </a>
          .
        </p>
      </section>

      {DOMAINS.map((domain) => (
        <section key={domain.id} className="rounded-lg border border-neutral-200 bg-white">
          <header className="flex items-baseline justify-between border-b border-neutral-200 px-4 py-3">
            <h2 className="text-xl font-semibold">
              {domain.id}. {domain.title}
            </h2>
            <span className="font-mono text-field">{domainWeight(domain).toFixed(1)}%</span>
          </header>
          <ul className="divide-y divide-neutral-100">
            {domain.skills.map((skill) => (
              <li key={skill.id} className="px-4 py-3">
                <div className="flex items-baseline justify-between gap-4">
                  <h3 className="font-medium">
                    {skill.id} {skill.title}
                  </h3>
                  <span className="shrink-0 font-mono text-sm text-neutral-500">{skill.weight}%</span>
                </div>
                <p className="mt-1 text-sm text-neutral-600">{skill.summary}</p>
                <p className="mt-2 flex flex-wrap gap-2 text-xs">
                  {skill.courses.map((c) => (
                    <a
                      key={c}
                      href={COURSES[c].url}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded bg-field/10 px-2 py-0.5 text-field-dark hover:bg-field/20"
                    >
                      {COURSES[c].title}
                    </a>
                  ))}
                  {skill.labs.map((l) => (
                    <span key={l} className="rounded bg-pigskin/10 px-2 py-0.5 text-pigskin">
                      {l}: {LABS[l]}
                    </span>
                  ))}
                  <span className="rounded bg-neutral-100 px-2 py-0.5 text-neutral-600">
                    {questionsForSkill(skill.id).length} questions
                  </span>
                </p>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

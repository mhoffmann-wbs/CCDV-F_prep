import { EXAM_FORMAT } from '../content/blueprint'
import type { DomainScore, ScoreReport } from './grading'

/** Mirrors the official score report: pass/fail, scaled score, percent correct by domain. */
export default function ScoreReportView({ report }: { report: ScoreReport }) {
  return (
    <section className="space-y-4">
      <h1 className="text-3xl font-bold">
        {report.passed ? '🏆 Pass' : 'Not yet: keep drilling'}
      </h1>
      <p className="text-lg">
        Estimated scaled score: <strong>{report.scaledEstimate}</strong> (pass at {EXAM_FORMAT.passingScaled}) ·{' '}
        {report.correct}/{report.total} correct
      </p>
      <p className="text-xs text-neutral-500">
        This is a linear estimate. The official exam uses an unpublished, criterion-referenced scale, so treat
        this number as a rough guide only.
      </p>
      <DomainTable byDomain={report.byDomain} />
    </section>
  )
}

/** Correct count and percentage per domain, in blueprint order. Shared by the mock report and practice. */
export function DomainTable({ byDomain }: { byDomain: readonly DomainScore[] }) {
  return (
    <table className="w-full max-w-xl text-sm">
      <thead>
        <tr className="border-b text-left text-neutral-500">
          <th className="py-1 font-medium">Domain</th>
          <th className="py-1 text-right font-medium">Correct</th>
          <th className="py-1 text-right font-medium">%</th>
        </tr>
      </thead>
      <tbody>
        {byDomain.map((d) => (
          <tr key={d.domainId} className="border-b border-neutral-100">
            <td className="py-1">
              {d.domainId}. {d.title}
            </td>
            <td className="py-1 text-right font-mono">
              {d.correct}/{d.total}
            </td>
            <td className="py-1 text-right font-mono">{Math.round((d.correct / d.total) * 100)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// Prints content coverage per skill against the PLAN.md targets.
// Run: npm run content:status
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { DOMAINS, questionTarget } from '../src/content/blueprint.ts'

const questionsDir = join(import.meta.dirname, '../src/content/questions')
const counts = new Map<string, number>()
for (const file of readdirSync(questionsDir).filter((f) => /^domain-\d\.json$/.test(f))) {
  for (const q of JSON.parse(readFileSync(join(questionsDir, file), 'utf8')) as { skillId: string }[]) {
    counts.set(q.skillId, (counts.get(q.skillId) ?? 0) + 1)
  }
}

let have = 0
let want = 0
for (const d of DOMAINS) {
  console.log(`\n${d.id}. ${d.title}`)
  for (const s of d.skills) {
    const n = counts.get(s.id) ?? 0
    const target = questionTarget(s)
    have += Math.min(n, target)
    want += target
    const mark = n >= target ? '✓' : ' '
    console.log(`  ${mark} ${s.id.padEnd(4)} ${s.title.padEnd(40)} ${String(n).padStart(3)} / ${target}`)
  }
}
console.log(`\nQuestions: ${have} / ${want} (${Math.round((have / want) * 100)}%)`)

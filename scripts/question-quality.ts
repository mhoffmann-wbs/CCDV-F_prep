// Prints answer-key balance and giveaway checks for question files.
// Run: npm run content:quality [-- <file.json> ...]   (default: the whole bank)
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import type { Question } from '../src/content/schema.ts'
import { analyzeQuestions } from '../src/content/questionQuality.ts'

const questionsDir = join(import.meta.dirname, '../src/content/questions')
const args = process.argv.slice(2)
const files = args.length
  ? args
  : readdirSync(questionsDir)
      .filter((f) => /^\d\.\d\.json$/.test(f))
      .map((f) => join(questionsDir, f))

const questions = files.flatMap((f) => JSON.parse(readFileSync(f, 'utf8')) as Question[])
const report = analyzeQuestions(questions)

const shares = Object.entries(report.letterShare)
  .sort()
  .map(([l, s]) => `${l} ${Math.round(s * 100)}%`)
  .join('  ')
console.log(`Items: ${questions.length} (${report.singleSelect} single, ${report.multiSelect} multi, official excluded)`)
console.log(`Key letters (single-select): ${shares}`)
console.log(`Key is longest option: ${Math.round(report.longestKeyShare * 100)}%`)
if (report.problems.length) {
  console.log('\nProblems:')
  for (const p of report.problems) console.log(`  - ${p}`)
  process.exitCode = 1
} else {
  console.log('\nNo problems found.')
}

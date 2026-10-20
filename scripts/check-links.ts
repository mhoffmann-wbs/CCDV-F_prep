// Checks every external link in the content (blueprint, lessons, questions).
// platform.claude.com answers missing pages with HTTP 200 and a generic title ("soft 404"),
// so a status check alone is not enough: we also inspect the page title.
// Run: npm run content:links   (needs network; not part of `npm test`)
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const root = join(import.meta.dirname, '..')
const contentDir = join(root, 'src/content')
const urls = new Map<string, Set<string>>() // url -> files that cite it

function collect(file: string) {
  const text = readFileSync(file, 'utf8')
  for (const match of text.matchAll(/https:\/\/[^\s"'`)\]>]+/g)) {
    const url = match[0].replace(/[.,;]+$/, '')
    if (!urls.has(url)) urls.set(url, new Set())
    urls.get(url)!.add(file.replace(`${root}/`, ''))
  }
}

collect(join(contentDir, 'blueprint.ts'))
for (const dir of ['lessons', 'questions']) {
  for (const f of readdirSync(join(contentDir, dir))) {
    if (/\.(mdx|json)$/.test(f)) collect(join(contentDir, dir, f))
  }
}

// API hosts mentioned in prose are endpoints, not pages.
const NOT_PAGES = [/^https:\/\/api\.anthropic\.com\/?$/]
for (const url of urls.keys()) if (NOT_PAGES.some((r) => r.test(url))) urls.delete(url)

// Pages behind a login or served as binaries can't be title-checked.
const SKIP_TITLE = [/skilljar\.com/, /\.pdf$/i, /everpath-course-content/]
const SOFT_404_TITLES = [/^Documentation \| Claude Platform$/i, /not found/i, /^404/]

async function check(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, { redirect: 'follow', signal: AbortSignal.timeout(20_000) })
    if (!res.ok) return `HTTP ${res.status}`
    if (SKIP_TITLE.some((r) => r.test(url))) return null
    const html = await res.text()
    const title = html.match(/<title[^>]*>([^<]*)<\/title>/i)?.[1].trim() ?? ''
    if (SOFT_404_TITLES.some((r) => r.test(title))) return `soft 404 (title: "${title}")`
    return null
  } catch (err) {
    return `fetch failed: ${(err as Error).message}`
  }
}

const entries = [...urls.entries()]
const failures: string[] = []
const CONCURRENCY = 8
for (let i = 0; i < entries.length; i += CONCURRENCY) {
  const batch = entries.slice(i, i + CONCURRENCY)
  const results = await Promise.all(batch.map(([url]) => check(url)))
  results.forEach((problem, j) => {
    if (problem) failures.push(`${batch[j][0]}\n    ${problem}\n    cited in: ${[...batch[j][1]].join(', ')}`)
  })
}

console.log(`Checked ${entries.length} unique links.`)
if (failures.length) {
  console.log(`\n${failures.length} broken:\n`)
  for (const f of failures) console.log(`  ${f}`)
  process.exitCode = 1
} else {
  console.log('All links OK.')
}

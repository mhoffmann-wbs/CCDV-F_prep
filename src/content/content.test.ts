import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { z } from 'zod'
import {
  DOMAINS,
  EXAM_FORMAT,
  SKILLS,
  allocateItems,
  domainWeight,
  questionTarget,
} from './blueprint'
import { LAB_CONTENT, REQUIRED_LAB_SECTIONS } from './labs'
import { LESSONS, REQUIRED_SECTIONS } from './lessons'
import { analyzeQuestions } from './questionQuality'
import { QUESTIONS, questionFiles } from './questions'
import { QuestionSchema } from './schema'

describe('blueprint', () => {
  it('skill weights sum to 100', () => {
    const total = SKILLS.reduce((sum, s) => sum + s.weight, 0)
    expect(total).toBeCloseTo(100, 5)
  })

  it('domain weights match Exam Guide §6', () => {
    expect(DOMAINS.map(domainWeight)).toEqual([14.7, 33.1, 3.1, 2.6, 16.8, 11.0, 8.1, 10.6])
  })

  it('has 25 skills with ids matching their domain', () => {
    expect(SKILLS).toHaveLength(25)
    for (const d of DOMAINS) {
      d.skills.forEach((s, i) => expect(s.id).toBe(`${d.id}.${i + 1}`))
    }
  })

  it('every skill maps to at least one course and lab', () => {
    for (const s of SKILLS) {
      expect(s.courses.length, s.id).toBeGreaterThan(0)
      expect(s.labs.length, s.id).toBeGreaterThan(0)
    }
  })

  it('question targets total about 303 (PLAN.md §2)', () => {
    expect(SKILLS.reduce((sum, s) => sum + questionTarget(s), 0)).toBe(303)
  })

  it('mock exam allocation sums to 53 and gives heavier skills at least as many items', () => {
    const alloc = allocateItems()
    expect([...alloc.values()].reduce((a, b) => a + b, 0)).toBe(EXAM_FORMAT.items)
    const sorted = [...SKILLS].sort((a, b) => b.weight - a.weight)
    for (let i = 1; i < sorted.length; i++) {
      expect(alloc.get(sorted[i - 1].id)!).toBeGreaterThanOrEqual(alloc.get(sorted[i].id)!)
    }
  })
})

describe('question bank', () => {
  it('every file parses against the schema', () => {
    for (const [path, raw] of Object.entries(questionFiles)) {
      const result = z.array(QuestionSchema).safeParse(raw)
      expect(result.success, `${path}: ${result.error?.message}`).toBe(true)
    }
  })

  it('questions live in the file of their skill', () => {
    for (const [path, raw] of Object.entries(questionFiles)) {
      const skillId = path.match(/\/(\d\.\d)\.json$/)?.[1]
      expect(skillId, `${path} must be named <skillId>.json`).toBeDefined()
      for (const q of raw as { id: string; skillId: string }[]) {
        expect(q.skillId, `${q.id} in ${path}`).toBe(skillId)
      }
    }
  })

  it('question ids are unique', () => {
    const ids = QUESTIONS.map((q) => q.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('numbered ids match their skill', () => {
    for (const q of QUESTIONS.filter((q) => !q.official)) {
      expect(q.id.startsWith(`q-${q.skillId}-`), q.id).toBe(true)
    }
  })

  it('has no answer-key giveaways or duplicate items (npm run content:quality)', () => {
    expect(analyzeQuestions(QUESTIONS).problems).toEqual([])
  })

  it('includes the three official Exam Guide samples', () => {
    expect(QUESTIONS.filter((q) => q.official).map((q) => q.id).sort()).toEqual([
      'official-1',
      'official-2',
      'official-3',
    ])
  })
})

describe('lessons', () => {
  // Read the raw MDX from disk: the MDX plugin would compile a `?raw` import.
  const lessonDir = join(import.meta.dirname, 'lessons')
  const lessonSources = Object.fromEntries(
    readdirSync(lessonDir)
      .filter((f) => f.endsWith('.mdx'))
      .map((f) => [f, readFileSync(join(lessonDir, f), 'utf8')]),
  )

  it('every blueprint skill has a lesson', () => {
    expect(SKILLS.filter((s) => !LESSONS.has(s.id)).map((s) => s.id)).toEqual([])
  })

  it('each file is named after the skill its meta declares', () => {
    for (const path of Object.keys(lessonSources)) {
      const fileId = path.match(/^(\d\.\d)\.mdx$/)?.[1]
      expect(fileId, path).toBeDefined()
      expect(LESSONS.get(fileId!), path).toBeDefined()
    }
  })

  it('every lesson has the required sections in order', () => {
    for (const [path, source] of Object.entries(lessonSources)) {
      const positions = REQUIRED_SECTIONS.map((heading) => source.indexOf(`\n${heading}`))
      expect(positions.every((p) => p >= 0), `${path} is missing a required section`).toBe(true)
      expect([...positions].sort((a, b) => a - b), `${path} sections out of order`).toEqual(positions)
    }
  })

  it('every lesson links only to https URLs', () => {
    for (const { meta } of LESSONS.values()) {
      for (const link of meta.links) expect(link.url.startsWith('https://'), link.url).toBe(true)
    }
  })
})

describe('labs', () => {
  const labDir = join(import.meta.dirname, 'labs')
  const labsRoot = join(import.meta.dirname, '..', '..', 'labs')

  it('every lab page has the required sections in order', () => {
    for (const f of readdirSync(labDir).filter((f) => f.endsWith('.mdx'))) {
      const source = readFileSync(join(labDir, f), 'utf8')
      const positions = REQUIRED_LAB_SECTIONS.map((heading) => source.indexOf(`\n${heading}`))
      expect(positions.every((p) => p >= 0), `${f} is missing a required section`).toBe(true)
      expect([...positions].sort((a, b) => a - b), `${f} sections out of order`).toEqual(positions)
      expect(LAB_CONTENT.get(f.replace('.mdx', '')), `${f} meta.labId must match its file name`).toBeDefined()
    }
  })

  it('every lab page points to a code folder with a starter and a solution', () => {
    // Python labs ship starter.py/solution.py; config-style labs (e.g. Claude Code) ship starter/ and solution/ folders.
    for (const { meta } of LAB_CONTENT.values()) {
      expect(meta.folder.startsWith(`${meta.labId}-`), meta.folder).toBe(true)
      for (const name of ['starter', 'solution']) {
        const dir = join(labsRoot, meta.folder)
        expect(existsSync(join(dir, `${name}.py`)) || existsSync(join(dir, name)), `${meta.folder}/${name}(.py|/)`).toBe(true)
      }
    }
  })

  it('lab step ids are unique within a lab', () => {
    for (const { meta } of LAB_CONTENT.values()) {
      const ids = meta.steps.map((s) => s.id)
      expect(new Set(ids).size, meta.labId).toBe(ids.length)
    }
  })
})

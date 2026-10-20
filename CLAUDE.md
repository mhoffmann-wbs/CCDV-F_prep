# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**`PLAN.md` is the build plan and sets the order of work.** It covers the skill-by-skill content map, the question-bank targets, the lab specs and the phases (§5 records what is done). Phases 0–4 are complete: the scaffold, the blueprint, the question schema, the content tests, the quiz engine (practice and mock exam), the progress store, all 25 lessons, and the full question bank (303 items, which meets every per-skill target and includes the 3 official samples). Everything marked *planned* below doesn't exist yet. As parts get built, update this file so it describes what actually exists.

## Purpose

This is an interactive study app for the **Claude Certified Developer – Foundations (CCDV-F)** exam. It has three pillars:
- **Learn**: one lesson for each of the 25 blueprint skills, linking to official docs and Skilljar courses.
- **Check**: practice and mock exams written in the style of the real exam.
- **Build**: ten NFL-themed hands-on labs that together form one capstone app called "Gridiron Assistant".

## Authoritative sources

- **Exam Guide v1.0** (July 2026) is the single source of truth for domains, skill weights and exam format. [PDF](https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2F6nizmqk8tpzpfjvt6qmmav7rh%2Fpublic%2F1783542875%2FClaude+Certified+Developer+%E2%80%93+Foundations+Exam+Guide.pdf)
- **Official prep path** (5 Skilljar courses, login required, so link to them and don't summarize them). [Path](https://anthropic-partners.skilljar.com/path/claude-certified-developer-foundations)

Use these, not third-party prep sites. If the guide gets a new version, update `src/content/blueprint.ts` first. The content tests then show which lessons and question pools need to change.

## Exam format the app must mirror

- 53 items in 120 minutes.
- Items are multiple-choice or multiple-response, and **each item states how many answers to select**.
- Pass mark is a scaled 720 on a 100–1,000 scale.
- The score report shows pass/fail, the scaled score, and percent correct per domain.
- Items are scenario-based ("which approach best fits…"), with one defensible answer and plausible distractors. Guide §8 has the 3 official samples.

## Architecture

- **Stack**: Vite 8 + React 19 + TypeScript 6, Tailwind v4 (theme colours `field`, `field-dark`, `chalk`, `pigskin` are defined in `src/index.css` via `@theme`), React Router 8 (imported from `react-router`), Zod 4, MDX (`@mdx-js/rollup`, wired up but not used yet), Vitest 5 + RTL, and oxlint for linting. It is a static SPA with no backend.
- **Progress** (`src/progress/store.ts`) is the only module that touches `localStorage`. It is a versioned store: on a version mismatch it discards the stored data, so bump `VERSION` and add a migration in `load()` when the shape changes. Components read it with `useProgress()` (`useSyncExternalStore`).
- **Quiz engine** (`src/quiz/`):
  - `grading.ts`: multiple-response items are scored all-or-nothing. `scoreExam` produces the official report shape (pass/fail, scaled score, per-domain results). The scaled score is a linear estimate and the UI must always label it as one.
  - `sampler.ts`: `buildMockExam` draws each skill's share from `allocateItems()`. When a skill's pool is too small, it fills the gap from the rest of the bank and scales the time limit to the real 120 min / 53 items pace. Pass `seededRng(n)` in tests.
  - `QuestionView`: renders both single- and multi-select items. It stops users selecting more than `selectCount`, and reveals every option's explanation. It doesn't shuffle options.
  - Routes in `App.tsx`: `/` (blueprint), `/learn` and `/learn/:skillId`, `/practice?skill=2.3` or `?domain=2`, `/mock`.
- **TypeScript projects**:
  - `tsconfig.app.json` covers app code and excludes tests.
  - `tsconfig.test.json` covers tests, adds Node types and allows `node:fs`.
  - `tsconfig.node.json` covers `vite.config.ts`.
  - Vitest runs without globals, so `src/test/setup.ts` registers Testing Library's `cleanup` explicitly.
- **Content is data.** Everything lives under `src/content/`, and the UI renders it generically. To add a lesson, question or lab, add data. Don't add new components for it.
  - `blueprint.ts`: 8 domains and 25 skills (ids like `"2.3"`), exact weights, Skilljar course mapping, lab mapping and exam-format constants. It also holds `questionTarget()` (pool size per skill) and `allocateItems()` (largest-remainder split of the 53 mock items). Mock-exam sampling, readiness scoring and the content tests all derive from this file.
  - `schema.ts`: the Zod `QuestionSchema`, with cross-field checks: `correct.length === selectCount`, correct ids must exist among the options, and `skillId` must be in the blueprint.
  - `questions/<skillId>.json`: one array per skill. Per-skill files let several writers work in parallel without conflicts. They are loaded and validated through `import.meta.glob` in `questions/index.ts`. Ids are `q-<skillId>-NNN`, or `official-N` for the Exam Guide samples, which also carry `official: true`.
  - `lessons/<skillId>.mdx` (e.g. `2.5.mdx`, which is the reference template). Each file exports `meta` (validated by `LessonMetaSchema`: `skillId`, `updated`, `tldr`, `links[]` to official docs). The body has `## Key concepts`, `## Exam traps` and `## On the field` (an NFL example ending with a pointer to a lab), in that order, and `content.test.ts` enforces this. Skilljar course and lab links come from the blueprint, so don't repeat them in the MDX. MDX is compiled with `remark-gfm`, so tables work, but a bare `<` or `{` in prose breaks the build: wrap it in backticks. `/learn/:skillId` renders the lesson with Tailwind `prose`. `LearnPage` is lazy-loaded in `App.tsx` because the lessons are the bulk of the bundle. Don't import `content/lessons` from any eagerly loaded page.
  - *Planned:* `labs/L<n>.mdx`.
- **`content.test.ts`** checks blueprint integrity (weights sum to 100, domain weights match the guide, allocation) and question-bank integrity (schema, file/skill match, unique ids). It also runs the anti-giveaway checks in `questionQuality.ts`:
  - no answer letter is the key in more than 40% of single-select items
  - the key is the longest option in at most 40% of them
  - no duplicate stems

  These checks skip the official samples, which keep their published order. Explanations must never mention option letters, so options can be reordered to rebalance the keys. The question *targets* are not enforced by tests. Track them with `npm run content:status`.
- **UI tests** (`src/pages/pages.test.tsx`) render `<App>` inside a `MemoryRouter` and run against the real question bank. Adding questions can change which item appears first, so write these tests to be independent of order.
- *Planned:* **`labs/`** is a separate TS workspace that learners run themselves with their own `ANTHROPIC_API_KEY`, using bundled fictional NFL JSON fixtures. The web app never calls the Claude API and never stores keys.

## Content rules

- Before writing API, model, pricing, Agent SDK or MCP details into lessons, questions or labs, check them with the `claude-api` skill. Never write them from memory. Skill 5.3 explicitly tests breaking changes across model releases.
- Write every question yourself. Never reproduce live exam content: candidates are under an NDA.
- Explanations should follow the reasoning style of the guide's sample rationales: say why the right answer fits the stated constraint, and why each distractor misses it.

## Commands

```bash
npm run dev             # Vite dev server
npm run build           # tsc -b + production build
npm run lint            # oxlint
npm test                # Vitest (run once); npm run test:watch for watch mode
npm run content:status  # question count per skill vs. target (Node runs the TS directly)
npm run content:quality [-- <file.json> ...]  # key-letter balance and giveaway checks, per file or whole bank
npm run content:links   # fetch every cited URL (needs network; not part of npm test)
npx vitest run src/content/content.test.ts   # single file
npx vitest run -t "blueprint"                # single test by name
```

Link checks must look at the page, not only the status code: platform.claude.com serves missing pages as HTTP 200 with the generic title "Documentation | Claude Platform". `content:links` detects this, so run it after adding or changing any `sourceLinks` or lesson links.

Vitest caches `import.meta.glob` results. If a newly added lesson or question file doesn't show up in tests, run `npx vitest --clearCache`.
